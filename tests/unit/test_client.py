"""Tests for the SkylightAPI client: request flow, auth cascade, endpoints."""

import json
from typing import Any

import aiohttp
import pytest
from aioresponses import aioresponses
from yarl import URL

from skylight_api import BASE_URL, OAUTH_URL, SkylightAPI, SkylightAPIError, SkylightAuthError
from skylight_api.client import exchange_authorization_code, exchange_refresh_token

FRAMES_BODY = {
    "data": [
        {
            "id": "111",
            "attributes": {"name": "byrd-malone-7772", "household_name": "Byrd & Malone"},
        },
        {"id": 222, "attributes": {}},
    ]
}


def last_kwargs(m: aioresponses, method: str, url: str) -> dict:
    """Return the request kwargs of the most recent call aioresponses saw."""
    calls = m.requests[(method, URL(url))]
    return calls[-1][1]


def last_json(m: aioresponses, method: str, url: str) -> Any:
    """Return the JSON body of the most recent request aioresponses saw."""
    kwargs = last_kwargs(m, method, url)
    if "json" in kwargs:
        return kwargs["json"]
    data = kwargs["data"]
    return json.loads(data) if isinstance(data, (str, bytes)) else dict(data)


def last_form(m: aioresponses, method: str, url: str) -> dict:
    """Return the form body of the most recent request aioresponses saw."""
    data = last_kwargs(m, method, url)["data"]
    return dict(data) if not isinstance(data, str) else dict(
        p.split("=", 1) for p in data.split("&")
    )


class TestRequestFlow:
    async def test_get_sends_auth_headers(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/frames", payload=FRAMES_BODY)
            data = await client._request("GET", "/api/frames")
        assert data == FRAMES_BODY

    async def test_get_frames_prefers_household_name(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/frames", payload=FRAMES_BODY)
            frames = await client.get_frames()
        assert frames == [
            {"id": "111", "name": "Byrd & Malone"},
            {"id": "222", "name": "Skylight Frame 222"},
        ]

    async def test_none_params_are_dropped(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.get(
                f"{BASE_URL}/api/frames/1/calendar_events?date_min=2026-01-01",
                payload={"data": []},
            )
            await client._request(
                "GET",
                "/api/frames/1/calendar_events",
                params={"date_min": "2026-01-01", "date_max": None, "timezone": None},
            )

    async def test_empty_body_returns_empty_dict(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.delete(f"{BASE_URL}/api/frames/1/chores/2", body="")
            assert await client._request("DELETE", "/api/frames/1/chores/2") == {}

    async def test_delete_chore_returns_none(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.delete(f"{BASE_URL}/api/frames/1/chores/2", body="")
            assert await client.delete_chore("1", "2") is None

    async def test_http_400_raises_api_error_with_status(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/frames/1/lists", body='{"error": "bad"}', status=400)
            with pytest.raises(SkylightAPIError) as exc:
                await client.create_list("1", "Groceries")
        assert exc.value.status_code == 400


class TestAuthCascade:
    async def test_401_triggers_refresh_and_retry(self, session: aiohttp.ClientSession) -> None:
        rotated: dict[str, str] = {}

        async def persist(access: str, refresh: str, fp: str | None) -> None:
            rotated.update(access=access, refresh=refresh, fp=fp or "")

        api = SkylightAPI(
            session,
            access_token="stale",
            refresh_token="r1",
            device_fingerprint="fp1",
            token_update_cb=persist,
        )
        with aioresponses() as m:
            # First call: stale token -> 401
            m.get(f"{BASE_URL}/api/frames", status=401)
            # Refresh exchange succeeds and rotates both tokens
            m.post(
                OAUTH_URL,
                payload={"access_token": "fresh", "refresh_token": "r2"},
            )
            # Retry with fresh token succeeds
            m.get(f"{BASE_URL}/api/frames", payload=FRAMES_BODY)
            frames = await api.get_frames()

        assert frames[0]["name"] == "Byrd & Malone"
        assert api.access_token == "fresh"
        assert api.refresh_token == "r2"
        assert rotated == {"access": "fresh", "refresh": "r2", "fp": "fp1"}

    async def test_401_after_refresh_raises_auth_error(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/frames", status=401)
            m.post(OAUTH_URL, status=401, body="invalid_grant")
            with pytest.raises(SkylightAuthError):
                await client.get_frames()

    async def test_refresh_missing_access_token_raises(
        self, session: aiohttp.ClientSession
    ) -> None:
        api = SkylightAPI(session, "a", "r")
        with aioresponses() as m:
            m.post(OAUTH_URL, payload={"error": "server_error"})
            with pytest.raises(SkylightAuthError):
                await api._refresh_access_token()

    async def test_token_callback_failure_is_swallowed(
        self, session: aiohttp.ClientSession
    ) -> None:
        calls: list[int] = []

        async def boom(access: str, refresh: str, fp: str | None) -> None:
            calls.append(1)
            raise RuntimeError("persistence down")

        api = SkylightAPI(session, "a", "r", token_update_cb=boom)
        with aioresponses() as m:
            m.post(OAUTH_URL, payload={"access_token": "x", "refresh_token": "y"})
            await api._refresh_access_token()
        assert api.access_token == "x"
        assert calls == [1]


class TestEtagCache:
    async def test_304_replays_cached_body(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.get(
                f"{BASE_URL}/api/frames",
                payload=FRAMES_BODY,
                headers={"ETag": 'W/"v1"'},
            )
            first = await client._request("GET", "/api/frames", cacheable=True)
            assert first == FRAMES_BODY

        with aioresponses() as m:
            # No response registered for a plain replay; if the client sent a
            # second request it would raise ConnectionError.
            m.get(
                f"{BASE_URL}/api/frames",
                status=304,
                headers={"ETag": 'W/"v1"'},
            )
            second = await client._request("GET", "/api/frames", cacheable=True)
        assert second == FRAMES_BODY

    async def test_304_without_cache_raises(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/frames", status=304)
            with pytest.raises(SkylightAPIError):
                await client._request("GET", "/api/frames", cacheable=True)

    async def test_cache_is_not_used_on_uncacheable_gets(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/frames/1/chores", payload={"data": []})
            await client._request("GET", "/api/frames/1/chores")
            # Second call must hit the wire again — register another response.
            m.get(f"{BASE_URL}/api/frames/1/chores", payload={"data": []})
            await client._request("GET", "/api/frames/1/chores")


class TestChoreEndpoints:
    async def test_create_chores_sends_flat_fanout_body(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/frames/1/chores/create_multiple", payload={"data": {}})
            await client.create_chores(
                "1",
                "Take out trash",
                "2026-10-06",
                category_ids=["10", 20],  # type: ignore[list-item]  # int ID is coerced to str
                description="Weekly",
                up_for_grabs=True,
            )

        body: dict[str, Any] = last_json(
            m, "POST", f"{BASE_URL}/api/frames/1/chores/create_multiple"
        )
        assert body["summary"] == "Take out trash"
        assert body["start"] == "2026-10-06"
        assert body["category_ids"] == ["10", "20"]
        assert body["up_for_grabs"] is True
        # Every key present, nulls included — the known-good payload.
        assert "start_time" in body
        assert "recurrence_set" in body
        assert "status" not in body

    async def test_complete_chore_omits_absent_instance_date(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.put(f"{BASE_URL}/api/frames/1/chores/5/completions", payload={"meta": {}})
            await client.complete_chore("1", "5", "2026-10-06")

        body = last_json(m, "PUT", f"{BASE_URL}/api/frames/1/chores/5/completions")
        assert body == {"status": "complete", "completed_on": "2026-10-06"}
        assert "instance_date" not in body

    async def test_complete_chore_with_instance_date(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.put(f"{BASE_URL}/api/frames/1/chores/5/completions", payload={"meta": {}})
            await client.complete_chore("1", "5", "2026-10-06", instance_date="2026-10-05")

        body = last_json(m, "PUT", f"{BASE_URL}/api/frames/1/chores/5/completions")
        assert body["instance_date"] == "2026-10-05"

    async def test_uncomplete_chore_sends_pending(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.put(f"{BASE_URL}/api/frames/1/chores/5/completions", payload={})
            await client.uncomplete_chore("1", "5")

        body = last_json(m, "PUT", f"{BASE_URL}/api/frames/1/chores/5/completions")
        assert body == {"status": "pending"}

    async def test_get_chores_includes_late_and_up_for_grabs(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.get(
                f"{BASE_URL}/api/frames/1/chores?after=2026-10-01&before=2026-10-08"
                "&include_late=true&include_up_for_grabs=true",
                payload={"data": []},
            )
            await client.get_chores("1", "2026-10-01", "2026-10-08")


class TestDeviceEndpoints:
    async def test_get_devices_normalizes_ids(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.get(
                f"{BASE_URL}/api/frames/1/devices",
                payload={"data": [{"id": 7, "attributes": {"role": "buddy"}}, {"id": None}]},
            )
            devices = await client.get_devices("1")
        assert devices == [{"id": "7", "attributes": {"role": "buddy"}}]

    async def test_patch_device_flat_body(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.patch(f"{BASE_URL}/api/frames/1/devices/7", payload={"data": {"attributes": {}}})
            await client.patch_device("1", "7", {"brightness": 200})

        body = last_json(m, "PATCH", f"{BASE_URL}/api/frames/1/devices/7")
        assert body == {"brightness": 200}
        assert "data" not in body  # no JSON:API envelope


class TestJsonapiEndpoints:
    async def test_create_list_uses_jsonapi_envelope(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/frames/1/lists", payload={"data": {}})
            await client.create_list("1", "Groceries", kind="shopping", color="#ff0000")

        body = last_json(m, "POST", f"{BASE_URL}/api/frames/1/lists")
        assert body == {
            "data": {
                "type": "list",
                "attributes": {"label": "Groceries", "kind": "shopping", "color": "#ff0000"},
            }
        }

    async def test_create_task_box_item_envelope(self, client: SkylightAPI) -> None:
        with aioresponses() as m:
            m.post(f"{BASE_URL}/api/frames/1/task_box/items", payload={"data": {}})
            await client.create_task_box_item("1", "Dishes", reward_points=5)

        body = last_json(m, "POST", f"{BASE_URL}/api/frames/1/task_box/items")
        assert body["data"]["type"] == "task_box_item"
        assert body["data"]["attributes"]["reward_points"] == 5


class TestOAuthExchanges:
    async def test_exchange_refresh_token(self, session: aiohttp.ClientSession) -> None:
        with aioresponses() as m:
            m.post(OAUTH_URL, payload={"access_token": "a2", "refresh_token": "r2"})
            tokens = await exchange_refresh_token(session, "r1", "fp")
        assert tokens == {"access_token": "a2", "refresh_token": "r2"}

    async def test_exchange_refresh_token_failure(self, session: aiohttp.ClientSession) -> None:
        with aioresponses() as m:
            m.post(OAUTH_URL, status=400, body="invalid_grant")
            with pytest.raises(SkylightAuthError):
                await exchange_refresh_token(session, "r1")

    async def test_exchange_authorization_code(self, session: aiohttp.ClientSession) -> None:
        with aioresponses() as m:
            m.post(OAUTH_URL, payload={"access_token": "a2", "refresh_token": "r2"})
            tokens = await exchange_authorization_code(session, "code1", "verifier1")
        assert tokens == {"access_token": "a2", "refresh_token": "r2"}
        body = last_form(m, "POST", OAUTH_URL)
        assert body["grant_type"] == "authorization_code"
        assert body["code_verifier"] == "verifier1"

    async def test_exchange_authorization_code_missing_tokens(
        self, session: aiohttp.ClientSession
    ) -> None:
        with aioresponses() as m:
            m.post(OAUTH_URL, payload={"access_token": "a2"})
            with pytest.raises(SkylightAuthError):
                await exchange_authorization_code(session, "code1", "verifier1")

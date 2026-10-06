# skylight_api

Async Python client library for the [Skylight Calendar](https://www.ourskylight.com/)
API. Designed for Home Assistant integrations: aiohttp-native, accepts an
external `ClientSession`, and rotates OAuth tokens through a callback so the
caller can persist them.

Part of the Skylight for Home Assistant ecosystem:

| Repo | Role |
|---|---|
| [MegaTheLEGEND/skylight_calendar](https://github.com/MegaTheLEGEND/skylight_calendar) | upstream integration |
| [devinslick/skylight_hass](https://github.com/devinslick/skylight_hass) | integration (HACS) |
| **devinslick/skylight-api** | this client library |

## Installation

```bash
pip install skylight_api
```

Requires Python 3.11+.

## Authentication

Skylight uses OAuth2 authorization code + PKCE. There is no headless
username/password path: you sign in through a browser once and keep the
tokens.

```python
from skylight_api import authorize_url, extract_code, pkce_pair

verifier, challenge = pkce_pair()
print(f"Open and sign in:\n{authorize_url(challenge)}")
# Skylight's OAuth server has a single registered redirect, so after signing
# in the browser lands on a URL containing ?code=... — paste that whole URL
# (or just the code) back:
pasted = input("Paste the callback URL or code: ")

import aiohttp
from skylight_api import exchange_authorization_code

async with aiohttp.ClientSession() as session:
    tokens = await exchange_authorization_code(session, extract_code(pasted), verifier)
    # Persist tokens["access_token"], tokens["refresh_token"] and the
    # device_fingerprint from the response headers/params as appropriate.
```

`exchange_refresh_token(session, refresh_token, device_fingerprint)` performs
the same grant for an existing refresh token — useful to verify stored
credentials before building a client.

## Usage

```python
import aiohttp
from skylight_api import SkylightAPI, SkylightAuthError, SkylightAPIError

async with aiohttp.ClientSession() as session:
    api = SkylightAPI(
        session,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        # Called whenever the 401-refresh cascade rotates tokens — persist them:
        token_update_cb=my_persist_callback,
    )

    frames = await api.get_frames()
    frame_id = frames[0]["id"]

    events = await api.get_calendar_events(
        frame_id, date_min="2026-10-01", date_max="2026-11-01", timezone="America/Chicago"
    )
    await api.create_calendar_event(
        frame_id, summary="Dentist", starts_at="2026-10-20T15:00:00",
        ends_at="2026-10-20T16:00:00", timezone="America/Chicago",
    )
```

On a `401` the client refreshes the access token once and retries; if the
refresh itself fails it raises `SkylightAuthError` (re-authentication
required). All other HTTP failures raise `SkylightAPIError` with
`status_code` and `response_body` attached; on `422` the library logs the
outgoing payload at DEBUG because Skylight's validation errors never name
what was sent.

### Endpoint coverage

Frames & devices (incl. Skylight Buddy alarms), calendar events (CRUD),
source calendars, categories/family members, lists & list items, chores
(create fan-out, complete/uncomplete with occurrence dates, delete), meals &
recipes, rewards (create/redeem), task box, and photo feeds. Media upload
(`upload_media`) performs the full dance: short-lived S3 credentials, AWS
SigV4-signed PUT, then registration with Skylight.

Several request shapes were captured from the Skylight web app; a few are
inferred and marked as such in the docstrings (with notes on what a `422`
means for them). The docstrings carry the wire knowledge — quirks like
"the completion endpoint wants the *series* id, never the composite id" and
"an on-demand chore must omit `instance_date` entirely" live there.

### ETag caching

Getters the web app caches with `If-None-Match` (frames, categories, devices,
source calendars, avatars, colors) accept `cacheable=True` behavior by
default: a `304` replays the cached body. Chores and rewards are never
cached — Skylight's validators don't reliably move when those records change.

## Development

```bash
uv venv --python 3.14 .venv
uv pip install -e '.[dev]' --python .venv/bin/python
.venv/bin/python -m pytest tests/unit -v
.venv/bin/python -m mypy skylight_api/
.venv/bin/python -m flake8 skylight_api/ tests/
```

CI runs lint + strict mypy and the unit test matrix on Python 3.11–3.14.
Publishing to PyPI happens automatically when a GitHub Release is published.

## License

MIT — see [LICENSE](LICENSE).

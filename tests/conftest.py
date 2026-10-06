"""Shared fixtures for tests."""

from collections.abc import AsyncIterator

import aiohttp
import pytest

from skylight_api import SkylightAPI


@pytest.fixture
async def session() -> AsyncIterator[aiohttp.ClientSession]:
    """An aiohttp session; aioresponses intercepts all traffic."""
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.fixture
def client(session: aiohttp.ClientSession) -> SkylightAPI:
    """A client with fixed test tokens."""
    return SkylightAPI(
        session,
        access_token="test-access",
        refresh_token="test-refresh",
        device_fingerprint="test-fp",
    )

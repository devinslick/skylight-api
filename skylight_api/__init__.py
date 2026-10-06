"""skylight_api — async Python client for the Skylight Calendar API.

Designed for Home Assistant integrations: aiohttp-native, accepts an external
ClientSession, and rotates tokens through a callback so the caller can persist
them.

Example:
    from skylight_api import SkylightAPI, exchange_refresh_token

    tokens = await exchange_refresh_token(session, refresh_token)
    api = SkylightAPI(session, tokens["access_token"], tokens["refresh_token"])
    frames = await api.get_frames()
"""

from .auth import authorize_url, extract_code, pkce_pair
from .client import (
    SkylightAPI,
    TokenUpdateCallback,
    exchange_authorization_code,
    exchange_refresh_token,
)
from .const import (
    API_VERSION,
    BASE_URL,
    CHORE_COMPLETE_STATUSES,
    CHORE_STATUS_COMPLETE,
    CHORE_STATUS_PENDING,
    OAUTH_AUTHORIZE_URL,
    OAUTH_CLIENT_ID,
    OAUTH_REDIRECT_URI,
    OAUTH_SCOPE,
    OAUTH_URL,
)
from .exceptions import SkylightAPIError, SkylightAuthError, SkylightError

__version__ = "0.1.0"

__all__ = [
    # Client
    "SkylightAPI",
    "TokenUpdateCallback",
    # OAuth helpers
    "authorize_url",
    "extract_code",
    "pkce_pair",
    "exchange_authorization_code",
    "exchange_refresh_token",
    # Constants
    "API_VERSION",
    "BASE_URL",
    "CHORE_COMPLETE_STATUSES",
    "CHORE_STATUS_COMPLETE",
    "CHORE_STATUS_PENDING",
    "OAUTH_AUTHORIZE_URL",
    "OAUTH_CLIENT_ID",
    "OAUTH_REDIRECT_URI",
    "OAUTH_SCOPE",
    "OAUTH_URL",
    # Exceptions
    "SkylightError",
    "SkylightAuthError",
    "SkylightAPIError",
]

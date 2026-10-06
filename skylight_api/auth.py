"""OAuth2 helpers: PKCE pair generation, authorize URL, code extraction.

The Skylight flow is authorization_code + PKCE (RFC 7636, S256). Skylight's
OAuth server has a single registered redirect URI, so headless clients
(Home Assistant) send the user to the authorize URL and have them paste back
either the raw ``code`` or the full callback URL from the browser's address
bar.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from urllib import parse as _urllib_parse

from .const import (
    OAUTH_AUTHORIZE_URL,
    OAUTH_CLIENT_ID,
    OAUTH_REDIRECT_URI,
    OAUTH_SCOPE,
)


def pkce_pair() -> tuple[str, str]:
    """Return (verifier, challenge) for RFC 7636 S256 PKCE."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def authorize_url(challenge: str) -> str:
    """Build the OAuth authorize URL for a PKCE challenge."""
    qs = _urllib_parse.urlencode(
        {
            "client_id": OAUTH_CLIENT_ID,
            "response_type": "code",
            "scope": OAUTH_SCOPE,
            "redirect_uri": OAUTH_REDIRECT_URI,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "prompt": "login",
        }
    )
    return f"{OAUTH_AUTHORIZE_URL}?{qs}"


def extract_code(raw: str) -> str | None:
    """Accept either a raw code or the full callback URL and return the code."""
    raw = raw.strip()
    if not raw:
        return None
    if "://" in raw or raw.startswith("/"):
        try:
            qs = _urllib_parse.parse_qs(_urllib_parse.urlparse(raw).query)
        except ValueError:
            return None
        return qs.get("code", [None])[0]
    # Strip a stray leading "code=" if the user pasted the fragment.
    if raw.lower().startswith("code="):
        return raw.split("=", 1)[1]
    return raw

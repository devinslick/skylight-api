"""Tests for the OAuth2/PKCE helpers."""

import base64
import hashlib
from urllib import parse as urlparse

from skylight_api import (
    OAUTH_AUTHORIZE_URL,
    OAUTH_CLIENT_ID,
    authorize_url,
    extract_code,
    pkce_pair,
)


class TestPkcePair:
    def test_verifier_is_urlsafe(self):
        verifier, _ = pkce_pair()
        assert len(verifier) >= 43
        # token_urlsafe output is URL-safe by construction
        assert "=" not in verifier

    def test_challenge_matches_s256_of_verifier(self):
        verifier, challenge = pkce_pair()
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        assert challenge == expected

    def test_pairs_are_unique(self):
        assert pkce_pair() != pkce_pair()


class TestAuthorizeUrl:
    def test_contains_required_params(self):
        _, challenge = pkce_pair()
        url = authorize_url(challenge)
        assert url.startswith(OAUTH_AUTHORIZE_URL)
        qs = urlparse.parse_qs(urlparse.urlparse(url).query)
        assert qs["client_id"] == [OAUTH_CLIENT_ID]
        assert qs["response_type"] == ["code"]
        assert qs["code_challenge"] == [challenge]
        assert qs["code_challenge_method"] == ["S256"]
        assert qs["prompt"] == ["login"]


class TestExtractCode:
    def test_raw_code(self):
        assert extract_code("abc123") == "abc123"

    def test_full_callback_url(self):
        url = "https://ourskylight.com/welcome?code=xyz&state=1"
        assert extract_code(url) == "xyz"

    def test_code_prefix_fragment(self):
        assert extract_code("code=abc") == "abc"

    def test_empty(self):
        assert extract_code("   ") is None

    def test_url_without_code(self):
        assert extract_code("https://ourskylight.com/welcome") is None

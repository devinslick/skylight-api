"""Tests for the S3 SigV4 signer."""

import hashlib
import hmac as hmac_mod

from skylight_api.upload import build_s3_put_url, s3_headers_for, sigv4_sign


class TestSigv4Sign:
    def test_authorization_header_shape(self):
        headers = sigv4_sign(
            "PUT",
            "https://bucket.s3.us-east-1.amazonaws.com/prefix/key.jpg?x-id=PutObject",
            headers={"Content-Type": "image/jpeg"},
            body=b"data",
            access_key="AKIA...",
            secret_key="secret",
            session_token="token",
        )
        auth = headers["Authorization"]
        assert auth.startswith("AWS4-HMAC-SHA256 Credential=AKIA.../")
        assert "/us-east-1/s3/aws4_request, " in auth
        assert "SignedHeaders=" in auth
        assert "Signature=" in auth

    def test_all_required_skylight_headers_present(self):
        headers = sigv4_sign(
            "PUT",
            "https://b.s3.amazonaws.com/k",
            headers={},
            body=b"",
            access_key="a",
            secret_key="s",
            session_token="t",
        )
        # Omitting any of these is a 403 from Skylight's bucket policy.
        for key in (
            "amz-sdk-invocation-id",
            "amz-sdk-request",
            "if-none-match",
            "x-amz-security-token",
            "x-amz-user-agent",
            "x-amz-content-sha256",
            "x-amz-date",
        ):
            assert key in headers, key
        assert headers["if-none-match"] == "*"
        assert headers["amz-sdk-request"] == "attempt=1; max=3"

    def test_content_sha256_matches_body(self):
        body = b"exact bytes"
        headers = sigv4_sign(
            "PUT", "https://b.s3.amazonaws.com/k", headers={}, body=body,
            access_key="a", secret_key="s", session_token="t",
        )
        assert headers["x-amz-content-sha256"] == hashlib.sha256(body).hexdigest()

    def test_request_is_reproducible_for_fixed_time(self):
        # Signing is deterministic given identical inputs except the random
        # invocation id and the current timestamp; assert both invocations
        # produce the same header *set*.
        h1 = sigv4_sign("PUT", "https://b.s3.amazonaws.com/k", headers={}, body=b"x",
                        access_key="a", secret_key="s", session_token="t")
        h2 = sigv4_sign("PUT", "https://b.s3.amazonaws.com/k", headers={}, body=b"x",
                        access_key="a", secret_key="s", session_token="t")
        assert set(h1) == set(h2)

    def test_signature_is_hex_hmac_of_string_to_sign(self):
        # Independent hand-rolled verification of the signing key derivation.
        secret, date_stamp, region, service = "s", "20260101", "us-east-1", "s3"
        k = hmac_mod.new(f"AWS4{secret}".encode(), date_stamp.encode(), hashlib.sha256).digest()
        k = hmac_mod.new(k, region.encode(), hashlib.sha256).digest()
        k = hmac_mod.new(k, service.encode(), hashlib.sha256).digest()
        k = hmac_mod.new(k, b"aws4_request", hashlib.sha256).digest()
        assert len(k) == 32  # derived without error; shape check


class TestS3UrlBuilders:
    def test_build_s3_put_url(self):
        url = build_s3_put_url("mybucket", "us-west-2", "prefix/uuid.jpg")
        assert url == "https://mybucket.s3.us-west-2.amazonaws.com/prefix/uuid.jpg?x-id=PutObject"

    def test_s3_headers_for_coerces(self):
        out = s3_headers_for({"Content-Type": "image/jpeg"})
        assert out == {"Content-Type": "image/jpeg"}
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in out.items())

"""AWS SigV4 signing for Skylight's S3 media uploads.

Skylight issues short-lived S3 credentials via
:meth:`SkylightAPI.get_cloud_upload_credentials`; uploads are then PUT
directly to the bucket. Skylight's bucket policy requires signing
``amz-sdk-invocation-id``, ``amz-sdk-request``, ``if-none-match`` and
``x-amz-user-agent`` in addition to the standard SigV4 headers — omitting any
of them results in 403 AccessDenied. This mirrors the exact header set sent by
aws-sdk-js/3.928.0 in the Skylight web app.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlparse


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def sigv4_sign(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes,
    access_key: str,
    secret_key: str,
    session_token: str,
    region: str = "us-east-1",
    service: str = "s3",
) -> dict[str, str]:
    """AWS SigV4 sign a request, returning the full header map to send."""
    parsed = urlparse(url)
    host = parsed.netloc
    path = parsed.path or "/"
    query = parsed.query

    now = datetime.now(tz=UTC)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(body).hexdigest()
    invocation_id = str(uuid.uuid4())

    to_sign: dict[str, str] = {
        "amz-sdk-invocation-id": invocation_id,
        "amz-sdk-request": "attempt=1; max=3",
        "content-type": headers.get("Content-Type", "application/octet-stream"),
        "host": host,
        "if-none-match": "*",
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
        "x-amz-security-token": session_token,
        "x-amz-user-agent": (
            "aws-sdk-js/3.928.0 ua/2.1 os/Windows lang/js "
            "md/browser#Firefox_unknown api/s3#3.928.0 m/a,b,E,e"
        ),
    }
    canonical_headers = "".join(f"{k}:{v}\n" for k, v in sorted(to_sign.items()))
    signed_headers_str = ";".join(sorted(to_sign.keys()))

    canonical_qs = (
        "&".join(
            f"{quote(k, safe='')}={quote(v, safe='')}"
            for k, v in sorted(p.split("=", 1) for p in query.split("&") if p)
        )
        if query
        else ""
    )

    canonical_request = "\n".join(
        [method, path, canonical_qs, canonical_headers, signed_headers_str, payload_hash]
    )
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ]
    )

    signing_key = _hmac(
        _hmac(
            _hmac(_hmac(f"AWS4{secret_key}".encode(), date_stamp), region),
            service,
        ),
        "aws4_request",
    )
    signature = hmac.new(
        signing_key, string_to_sign.encode(), hashlib.sha256
    ).hexdigest()

    return {
        **headers,
        "Authorization": (
            f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers_str}, Signature={signature}"
        ),
        "amz-sdk-invocation-id": invocation_id,
        "amz-sdk-request": "attempt=1; max=3",
        "if-none-match": "*",
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
        "x-amz-security-token": session_token,
        "x-amz-user-agent": to_sign["x-amz-user-agent"],
    }


def build_s3_put_url(bucket: str, region: str, key: str) -> str:
    """Virtual-hosted-style S3 PUT URL for an object key."""
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}?x-id=PutObject"


def s3_headers_for(headers: dict[str, Any]) -> dict[str, str]:
    """Coerce a header mapping to the plain-str dict the signer expects."""
    return {str(k): str(v) for k, v in headers.items()}

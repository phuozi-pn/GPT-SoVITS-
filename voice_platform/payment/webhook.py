"""Payment provider helpers."""

from __future__ import annotations

import hashlib
import hmac
from uuid import uuid4


def new_provider_ref(*, prefix: str = "chk") -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def sign_webhook_payload(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_webhook_signature(secret: str, body: bytes, signature: str | None) -> bool:
    if not secret or not signature:
        return False
    expected = sign_webhook_payload(secret, body)
    return hmac.compare_digest(expected, signature.strip())

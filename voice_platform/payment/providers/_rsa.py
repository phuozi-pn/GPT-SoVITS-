"""RSA helpers for WeChat Pay / Alipay signing."""

from __future__ import annotations

import base64
from pathlib import Path

from voice_platform.payment.providers.base import PaymentProviderError


def load_private_key_pem(*, path: str = "", content: str = "") -> object:
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
    except ImportError as exc:
        raise PaymentProviderError(
            "CRYPTO_REQUIRED",
            "Install cryptography for WeChat/Alipay providers",
        ) from exc

    pem = content.strip()
    if not pem and path:
        pem = Path(path).read_text(encoding="utf-8")
    if not pem:
        raise PaymentProviderError("KEY_MISSING", "Payment private key not configured")
    key = load_pem_private_key(pem.encode("utf-8"), password=None)
    return key


def sign_sha256_rsa(message: str, private_key) -> str:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    sig = private_key.sign(
        message.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(sig).decode("ascii")

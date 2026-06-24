from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from voice_platform.config import get_settings


def _fernet() -> Fernet:
    secret = (get_settings().jwt_secret or "dev-change-me-in-production-32bytes-min!!").encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt_credential(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_credential(cipher: str) -> str:
    try:
        return _fernet().decrypt(cipher.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("credential decrypt failed") from exc

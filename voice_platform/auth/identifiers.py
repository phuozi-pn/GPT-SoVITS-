"""Login identifier helpers (phone / email)."""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> str:
    normalized = normalize_email(email)
    if not _EMAIL_RE.match(normalized):
        raise ValueError("invalid email")
    return normalized


def email_otp_key(email: str) -> str:
    return f"email:{normalize_email(email)}"


def mask_email(email: str) -> str:
    normalized = normalize_email(email)
    local, _, domain = normalized.partition("@")
    if not domain:
        return "用户"
    if len(local) <= 2:
        return f"*@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"

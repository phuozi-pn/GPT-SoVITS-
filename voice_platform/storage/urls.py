"""Resolve storage URIs to public HTTP URLs."""

from __future__ import annotations

from voice_platform.storage.local import LocalStorage


def resolve_public_url(uri: str | None) -> str | None:
    if not uri:
        return None
    text = uri.strip()
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if text.startswith("local://"):
        rel = text.removeprefix("local://")
        return LocalStorage().public_url(rel)
    if not text.startswith("/") and "/" in text:
        return LocalStorage().public_url(text)
    return None

"""Resolve user training asset paths from storage URIs."""

from __future__ import annotations

from pathlib import Path

from voice_platform.config import get_settings


def resolve_storage_uri(uri: str) -> Path:
    """Map local:// or absolute path to a host file path."""
    raw = (uri or "").strip()
    if not raw:
        raise FileNotFoundError("empty storage uri")

    if raw.startswith("local://"):
        rel = raw.removeprefix("local://")
        path = Path(get_settings().storage_root) / rel
    elif raw.startswith("engine://"):
        rel = raw.removeprefix("engine://")
        root = get_settings().engine_train_root
        if not root:
            raise FileNotFoundError("ENGINE_TRAIN_ROOT not set for engine:// uri")
        path = Path(root) / rel
    else:
        path = Path(raw)

    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"asset not found: {uri} -> {resolved}")
    return resolved

from __future__ import annotations

from pathlib import Path


def is_cloud_train_configured(settings) -> bool:
    """True when admin has enabled SSH cloud train with a reachable host."""
    if not settings.cloud_train_enabled:
        return False
    host = (settings.cloud_train_ssh_host or "").strip()
    if not host:
        return False
    key = (settings.cloud_train_ssh_key_path or "").strip()
    if key and not Path(key).expanduser().is_file():
        return False
    return True

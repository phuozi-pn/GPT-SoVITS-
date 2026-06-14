from __future__ import annotations

import os
import wave
from pathlib import Path
from uuid import UUID

from voice_platform.config import ensure_storage_root, get_settings


class LocalStorage:
    def __init__(self, root: str | None = None) -> None:
        self._root = Path(root or ensure_storage_root())

    def save_bytes(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        data: bytes,
        ext: str = "wav",
        relative_name: str | None = None,
    ) -> str:
        if relative_name:
            rel = Path(str(user_id)) / relative_name
            if not rel.suffix:
                rel = rel.with_suffix(f".{ext}")
        else:
            rel = Path(str(user_id)) / "synthesis" / f"{job_id}.{ext}"
        path = self._root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return rel.as_posix()

    def public_url(self, rel_path: str) -> str:
        base = get_settings().storage_public_base_url.rstrip("/")
        return f"{base}/{rel_path}"

    def absolute_path(self, rel_path: str) -> str:
        return str((self._root / rel_path).resolve())

    def save_training_asset(
        self,
        *,
        user_id: UUID,
        asset_id: UUID,
        data: bytes,
        ext: str = "wav",
    ) -> tuple[str, str]:
        """Returns (storage_uri local://..., absolute_path)."""
        rel = Path(str(user_id)) / "training" / f"{asset_id}.{ext}"
        path = self._root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"local://{rel.as_posix()}", str(path.resolve())

    @staticmethod
    def wav_duration_sec(path: str) -> float:
        with wave.open(path, "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())

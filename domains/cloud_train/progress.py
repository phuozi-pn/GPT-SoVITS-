from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID


def cloud_train_progress_path(*, storage_root: str, job_id: UUID) -> Path:
    return Path(storage_root) / "cloud_train" / str(job_id) / "progress.json"


def read_cloud_train_progress(*, storage_root: str, job_id: UUID) -> dict | None:
    path = cloud_train_progress_path(storage_root=storage_root, job_id=job_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

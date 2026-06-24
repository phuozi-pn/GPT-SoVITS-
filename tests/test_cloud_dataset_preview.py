from __future__ import annotations

import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from domains.cloud_train.preview_service import CloudDatasetPreviewService, DatasetPreviewError


def _write_wav(path: Path, duration_sec: float = 5.0) -> None:
    n = int(duration_sec * 32000)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(32000)
        wf.writeframes(b"\x01\x00" * n)


def test_preview_requires_locked_asset():
    user = uuid4()
    asset_id = uuid4()
    asset = SimpleNamespace(
        owner_user_id=user,
        locked=False,
        qc_passed=True,
        storage_uri="local://x.wav",
        qc_result_json={"ref_text": "你好"},
    )
    session = MagicMock()
    repo = MagicMock()
    repo.get_asset.return_value = asset
    svc = CloudDatasetPreviewService(session)
    svc._voices = repo
    with pytest.raises(DatasetPreviewError) as exc:
        svc.preview(owner_user_id=user, asset_id=asset_id)
    assert exc.value.code == "ASSET_NOT_LOCKED"


def test_preview_returns_segments(tmp_path, monkeypatch):
    user = uuid4()
    asset_id = uuid4()
    wav = tmp_path / "train.wav"
    _write_wav(wav, 8.0)
    asset = SimpleNamespace(
        owner_user_id=user,
        locked=True,
        qc_passed=True,
        storage_uri="local://train.wav",
        qc_result_json={"ref_text": "测试参考文本用于切分预览。"},
    )
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    from voice_platform.config import get_settings

    get_settings.cache_clear()

    session = MagicMock()
    repo = MagicMock()
    repo.get_asset.return_value = asset

    with patch("domains.cloud_train.preview_service.resolve_storage_uri", return_value=wav):
        svc = CloudDatasetPreviewService(session)
        svc._voices = repo
        out = svc.preview(owner_user_id=user, asset_id=asset_id, use_asr=False)
    assert out["segment_count"] >= 1
    assert out["segments"][0]["audio_url"].startswith("/files/")
    get_settings.cache_clear()

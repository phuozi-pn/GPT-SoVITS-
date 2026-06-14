"""Tests for engine weights import and CSV batch parsing."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from domains.projects.service import ProjectServiceError, _parse_csv
from domains.voices.import_service import EngineWeightsImportService, ImportServiceError
from voice_platform.config import get_settings
from voice_platform.job.schemas import ImportEngineWeightsRequest


@pytest.fixture
def engine_with_weights(tmp_path, monkeypatch):
    engine = tmp_path / "engine"
    gpt_dir = engine / "GPT_weights_v2Pro"
    sovits_dir = engine / "SoVITS_weights_v2Pro"
    samples = engine / "samples"
    gpt_dir.mkdir(parents=True)
    sovits_dir.mkdir(parents=True)
    samples.mkdir()
    (gpt_dir / "test.ckpt").write_bytes(b"x" * 100)
    (sovits_dir / "test.pth").write_bytes(b"y" * 100)
    ref = tmp_path / "ref.wav"
    import wave

    with wave.open(str(ref), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(32000)
        wf.writeframes(b"\x00\x00" * 32000)
    monkeypatch.setenv("ENGINE_TRAIN_ROOT", str(engine))
    monkeypatch.setenv("ENGINE_TRAIN_ROOT_IN_DOCKER", "/workspace/GPT-SoVITS")
    get_settings.cache_clear()
    yield engine, ref
    get_settings.cache_clear()


def test_import_weights(engine_with_weights):
    engine, ref = engine_with_weights
    user = uuid4()
    voice_id = uuid4()
    version_id = uuid4()
    body = ImportEngineWeightsRequest(
        voice_name="test-voice",
        label="v1",
        engine_gpt_weights="GPT_weights_v2Pro/test.ckpt",
        engine_sovits_weights="SoVITS_weights_v2Pro/test.pth",
        ref_audio_host_path=str(ref),
        ref_text="ref text",
    )

    from types import SimpleNamespace

    voice_row = SimpleNamespace(id=voice_id, name="test-voice", owner_user_id=user)
    version_row = SimpleNamespace(
        id=version_id,
        voice_id=voice_id,
        version=1,
        model_tag="gsv-v2pro-20250606",
        ref_text="ref text",
        created_at=None,
        metadata_json={
            "label": "v1",
            "imported": True,
            "engine_gpt_weights": "GPT_weights_v2Pro/test.ckpt",
        },
    )

    session = MagicMock()
    with patch("domains.voices.import_service.VoiceRepository") as voices_cls, patch(
        "domains.voices.import_service.VoiceVersionRepository"
    ) as versions_cls:
        voices_cls.return_value.create_voice.return_value = voice_row
        versions_cls.return_value.next_version_number.return_value = 1
        versions_cls.return_value.create_version.return_value = version_row

        svc = EngineWeightsImportService(session)
        out = svc.import_weights(owner_user_id=user, body=body)

    assert out.imported is True
    assert out.ref_text == "ref text"
    assert out.voice_version_id == version_id
    assert list((engine / "samples").glob("platform_ref_*.wav"))


def test_import_weights_missing_gpt(engine_with_weights):
    engine, ref = engine_with_weights
    body = ImportEngineWeightsRequest(
        voice_name="test-voice",
        engine_gpt_weights="GPT_weights_v2Pro/missing.ckpt",
        engine_sovits_weights="SoVITS_weights_v2Pro/test.pth",
        ref_audio_host_path=str(ref),
        ref_text="ref text",
    )
    svc = EngineWeightsImportService(MagicMock())
    with pytest.raises(ImportServiceError) as exc:
        svc.import_weights(owner_user_id=uuid4(), body=body)
    assert exc.value.code == "GPT_WEIGHTS_NOT_FOUND"


def test_parse_csv_roles():
    role_id = uuid4()
    role_map = {"龙宫": role_id}
    csv_bytes = "role,text\n龙宫,你好世界\n".encode("utf-8")
    lines = _parse_csv(csv_bytes, role_map)
    assert len(lines) == 1
    assert lines[0].text == "你好世界"
    assert lines[0].voice_version_id == role_id


def test_parse_csv_chinese_headers():
    role_id = uuid4()
    csv_bytes = "角色,台词\n龙宫,台词一\n".encode("utf-8")
    lines = _parse_csv(csv_bytes, {"龙宫": role_id})
    assert len(lines) == 1
    assert lines[0].text == "台词一"


def test_parse_csv_unknown_role():
    csv_bytes = "role,text\n未知,台词\n".encode("utf-8")
    with pytest.raises(ProjectServiceError) as exc:
        _parse_csv(csv_bytes, {"龙宫": uuid4()})
    assert exc.value.code == "ROLE_UNBOUND"

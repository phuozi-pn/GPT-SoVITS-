from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from domains.training.validate import TrainingServiceError, cloud_train_issues, validate_train_backend
from domains.voices.import_service import EngineWeightsImportService, ImportServiceError
from domains.voices.weight_registration import EngineWeightsRegistration, register_engine_weights_version


def test_validate_train_backend_cloud_requires_profile_or_env(monkeypatch):
    monkeypatch.setenv("TRAIN_MOCK", "false")
    monkeypatch.setenv("ENGINE_TRAIN_ROOT", "/tmp/nonexistent-engine")
    from voice_platform.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(TrainingServiceError) as exc:
        validate_train_backend("cloud")
    assert exc.value.code in ("ENGINE_ROOT_MISSING", "CLOUD_GPU_NOT_CONNECTED")
    get_settings.cache_clear()


def test_cloud_train_issues_lists_train_mock(monkeypatch):
    monkeypatch.setenv("TRAIN_MOCK", "true")
    from voice_platform.config import get_settings

    get_settings.cache_clear()
    issues = cloud_train_issues()
    assert any("TRAIN_MOCK" in i for i in issues)
    get_settings.cache_clear()


def test_register_engine_weights_version(tmp_path, monkeypatch):
    engine = tmp_path / "engine"
    gpt_dir = engine / "GPT_weights_v2Pro"
    sovits_dir = engine / "SoVITS_weights_v2Pro"
    gpt_dir.mkdir(parents=True)
    sovits_dir.mkdir(parents=True)
    (gpt_dir / "a.ckpt").write_bytes(b"x")
    (sovits_dir / "b.pth").write_bytes(b"y")
    ref = tmp_path / "ref.wav"
    import wave

    with wave.open(str(ref), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(32000)
        wf.writeframes(b"\x00\x00" * (32000 * 6))
    monkeypatch.setenv("ENGINE_TRAIN_ROOT", str(engine))
    monkeypatch.setenv("ENGINE_TRAIN_ROOT_IN_DOCKER", "/workspace/GPT-SoVITS")
    from voice_platform.config import get_settings

    get_settings.cache_clear()

    voice_id = uuid4()
    owner = uuid4()
    session = object()
    row = type("Row", (), {"id": uuid4(), "version": 1})()

    with patch("domains.voices.weight_registration.VoiceVersionRepository") as repo_cls:
        repo_cls.return_value.next_version_number.return_value = 1
        repo_cls.return_value.create_version.return_value = row
        out = register_engine_weights_version(
            session=session,
            reg=EngineWeightsRegistration(
                voice_id=voice_id,
                owner_user_id=owner,
                gpt_rel="GPT_weights_v2Pro/a.ckpt",
                sovits_rel="SoVITS_weights_v2Pro/b.pth",
                ref_src_path=ref,
                ref_text="hello",
            ),
        )
    assert out is row
    assert list((engine / "samples").glob("platform_ref_*.wav"))
    get_settings.cache_clear()


def test_import_uploaded_files(tmp_path, monkeypatch):
    engine = tmp_path / "engine"
    gpt_dir = engine / "GPT_weights_v2Pro"
    sovits_dir = engine / "SoVITS_weights_v2Pro"
    gpt_dir.mkdir(parents=True)
    sovits_dir.mkdir(parents=True)
    monkeypatch.setenv("ENGINE_TRAIN_ROOT", str(engine))
    monkeypatch.setenv("ENGINE_TRAIN_ROOT_IN_DOCKER", "/workspace/GPT-SoVITS")
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    from voice_platform.config import get_settings

    get_settings.cache_clear()

    user = uuid4()
    voice_id = uuid4()
    version_id = uuid4()
    from types import SimpleNamespace

    voice_row = SimpleNamespace(id=voice_id, name="upload-voice", owner_user_id=user)
    version_row = SimpleNamespace(
        id=version_id,
        voice_id=voice_id,
        version=1,
        model_tag="gsv-v2pro-20250606",
        ref_text="ref",
        created_at=None,
        metadata_json={"label": "v1", "imported": True},
    )
    import wave

    buf = __import__("io").BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(32000)
        wf.writeframes(b"\x00\x00" * 8000)
    ref_bytes = buf.getvalue()

    session = __import__("unittest.mock").mock.MagicMock()
    with patch("domains.voices.import_service.VoiceRepository") as voices_cls, patch(
        "domains.voices.import_service.VoiceVersionRepository"
    ) as versions_cls, patch("domains.voices.import_service.register_engine_weights_version") as reg:
        voices_cls.return_value.create_voice.return_value = voice_row
        versions_cls.return_value.next_version_number.return_value = 1
        reg.return_value = version_row
        svc = EngineWeightsImportService(session)
        out = svc.import_uploaded_files(
            owner_user_id=user,
            voice_name="upload-voice",
            ref_text="ref",
            gpt_bytes=b"gpt-bytes",
            sovits_bytes=b"sovits-bytes",
            ref_bytes=ref_bytes,
        )
    assert out.voice_version_id == version_id
    assert list((engine / "GPT_weights_v2Pro").glob("import_*.ckpt"))
    get_settings.cache_clear()

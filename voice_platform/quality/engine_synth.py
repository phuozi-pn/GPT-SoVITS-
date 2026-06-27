"""Synchronous eval synthesis for quality scoring."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session
from voice_platform.config import get_settings
from voice_platform.job.models import VoiceVersionRow
from voice_platform.job.schemas import InferPayload
from workers.infer.runner import EngineAdapter, InferContext, MockEngineAdapter, synthesize_payload


def synthesize_eval_wav(
    *,
    session: Session,
    voice: VoiceVersionRow,
    text: str,
    use_mock: bool | None = None,
) -> bytes:
    settings = get_settings()
    mock = settings.engine_mock if use_mock is None else use_mock
    adapter = MockEngineAdapter() if mock else EngineAdapter()
    payload = InferPayload(
        voice_version_id=voice.id,
        text=text,
        format="wav",
        skip_quota=True,
    )
    return synthesize_payload(
        adapter=adapter,
        session=session,
        job_id=uuid4(),
        owner_user_id=voice.owner_user_id,
        payload=payload,
    )


def load_ref_wav_bytes(ref_uri: str | None) -> bytes | None:
    if not ref_uri:
        return None
    from pathlib import Path

    from voice_platform.storage.local import LocalStorage

    if ref_uri.startswith("local://"):
        rel = ref_uri.removeprefix("local://")
        path = LocalStorage().absolute_path(rel)
        if Path(path).is_file():
            return Path(path).read_bytes()
    return None


def load_ref_wav_bytes_for_voice(voice: VoiceVersionRow) -> bytes | None:
    from voice_platform.engine.ref_audio import voice_ref_host_path

    host = voice_ref_host_path(voice)
    if host is not None and host.is_file():
        return host.read_bytes()
    return load_ref_wav_bytes(voice.ref_audio_uri)

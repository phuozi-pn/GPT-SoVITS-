from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from voice_platform.config import get_settings
from voice_platform.engine.train_dataset import ensure_engine_ref_wav
from voice_platform.job.repository import VoiceVersionRepository
from voice_platform.job.schemas import MODEL_TAG_V2PRO


@dataclass(frozen=True)
class EngineWeightsRegistration:
    voice_id: UUID
    owner_user_id: UUID
    gpt_rel: str
    sovits_rel: str
    ref_src_path: Path
    ref_text: str
    model_tag: str = MODEL_TAG_V2PRO
    label: str = ""
    ref_name_prefix: str = "platform_ref"
    text_lang: str = "zh"
    text_split_method: str = "cut0"
    temperature: float = 0.78
    speed_factor: float = 1.05
    top_p: float = 1.0
    extra_metadata: dict[str, Any] = field(default_factory=dict)


def register_engine_weights_version(
    *,
    session,
    reg: EngineWeightsRegistration,
) -> Any:
    """Copy ref wav + register a finetuned VoiceVersion under ENGINE_TRAIN_ROOT."""
    settings = get_settings()
    engine_root = Path(settings.engine_train_root).resolve()
    gpt_rel = reg.gpt_rel.replace("\\", "/").lstrip("/")
    sovits_rel = reg.sovits_rel.replace("\\", "/").lstrip("/")
    gpt_path = engine_root / Path(gpt_rel)
    sovits_path = engine_root / Path(sovits_rel)

    samples_dir = engine_root / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    ref_name = f"{reg.ref_name_prefix}_{reg.voice_id.hex[:12]}.wav"
    ref_dst = samples_dir / ref_name
    ensure_engine_ref_wav(reg.ref_src_path, ref_dst)
    ref_host = str(ref_dst.resolve())
    docker_engine = settings.engine_train_root_in_docker.rstrip("/")
    ref_in_container = f"{docker_engine}/samples/{ref_name}"

    versions = VoiceVersionRepository(session)
    label = reg.label.strip() or f"v{versions.next_version_number(reg.voice_id)}"
    metadata = {
        "mock": False,
        "imported": True,
        "label": label,
        "engine_gpt_weights": gpt_rel,
        "engine_sovits_weights": sovits_rel,
        "engine_gpt_path": str(gpt_path),
        "engine_sovits_path": str(sovits_path),
        "engine_ref_audio_path": ref_host,
        "engine_ref_audio_container": ref_in_container,
        "engine_root": str(engine_root),
        "text_lang": reg.text_lang,
        "prompt_lang": reg.text_lang,
        "text_split_method": reg.text_split_method,
        "temperature": reg.temperature,
        "speed_factor": reg.speed_factor,
        "top_p": reg.top_p,
        "tune_preset": "cut0_t078_sp105",
        **reg.extra_metadata,
    }
    return versions.create_version(
        voice_id=reg.voice_id,
        owner_user_id=reg.owner_user_id,
        model_tag=reg.model_tag,
        checkpoint_uri=f"engine://{sovits_rel}",
        ref_audio_uri=ref_in_container,
        ref_text=reg.ref_text.strip(),
        metadata=metadata,
    )

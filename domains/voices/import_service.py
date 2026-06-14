from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID

from voice_platform.config import get_settings
from voice_platform.job.repository import VoiceRepository, VoiceVersionRepository
from voice_platform.job.schemas import ImportEngineWeightsRequest, MODEL_TAG_V2PRO, VoiceVersionSummary


class ImportServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class EngineWeightsImportService:
    """Register GPT-SoVITS weights (already on host) as a platform VoiceVersion."""

    def __init__(self, session) -> None:
        self._session = session
        self._voices = VoiceRepository(session)
        self._versions = VoiceVersionRepository(session)
        self._settings = get_settings()

    def import_weights(
        self,
        *,
        owner_user_id: UUID,
        body: ImportEngineWeightsRequest,
    ) -> VoiceVersionSummary:
        engine_root = Path(self._settings.engine_train_root).resolve()
        if not engine_root.is_dir():
            raise ImportServiceError(
                "ENGINE_ROOT_MISSING",
                f"ENGINE_TRAIN_ROOT not found: {engine_root}",
                500,
            )

        gpt_rel = body.engine_gpt_weights.replace("\\", "/").lstrip("/")
        sovits_rel = body.engine_sovits_weights.replace("\\", "/").lstrip("/")
        gpt_path = engine_root / Path(gpt_rel)
        sovits_path = engine_root / Path(sovits_rel)
        if not gpt_path.is_file():
            raise ImportServiceError("GPT_WEIGHTS_NOT_FOUND", f"Missing: {gpt_path}")
        if not sovits_path.is_file():
            raise ImportServiceError("SOVITS_WEIGHTS_NOT_FOUND", f"Missing: {sovits_path}")

        ref_src = Path(body.ref_audio_host_path).expanduser().resolve()
        if not ref_src.is_file():
            raise ImportServiceError("REF_AUDIO_NOT_FOUND", f"Missing ref wav: {ref_src}")

        if body.voice_id:
            voice = self._voices.get_voice(body.voice_id)
            if not voice or voice.owner_user_id != owner_user_id:
                raise ImportServiceError("VOICE_NOT_FOUND", "Voice not found", 404)
        else:
            voice = self._voices.create_voice(owner_user_id=owner_user_id, name=body.voice_name)

        samples_dir = engine_root / "samples"
        samples_dir.mkdir(parents=True, exist_ok=True)
        ref_name = f"platform_ref_{voice.id.hex[:12]}.wav"
        ref_dst = samples_dir / ref_name
        shutil.copy2(ref_src, ref_dst)
        docker_engine = self._settings.engine_train_root_in_docker.rstrip("/")
        ref_in_container = f"{docker_engine}/samples/{ref_name}"

        label = body.label.strip() or f"v{self._versions.next_version_number(voice.id)}"
        metadata = {
            "mock": False,
            "imported": True,
            "label": label,
            "engine_gpt_weights": gpt_rel,
            "engine_sovits_weights": sovits_rel,
            "engine_gpt_path": str(gpt_path),
            "engine_sovits_path": str(sovits_path),
            "engine_ref_audio_path": ref_in_container,
            "engine_root": str(engine_root),
            "text_lang": "zh",
            "prompt_lang": "zh",
            "text_split_method": body.text_split_method,
            "temperature": body.temperature,
            "speed_factor": body.speed_factor,
            "top_p": body.top_p,
            "tune_preset": "cut0_t078_sp105",
        }

        row = self._versions.create_version(
            voice_id=voice.id,
            owner_user_id=owner_user_id,
            model_tag=body.model_tag or MODEL_TAG_V2PRO,
            checkpoint_uri=f"engine://{sovits_rel}",
            ref_audio_uri=ref_in_container,
            ref_text=body.ref_text.strip(),
            metadata=metadata,
        )
        return _version_summary(row, voice.name)


def _version_summary(row, voice_name: str) -> VoiceVersionSummary:
    meta = row.metadata_json or {}
    return VoiceVersionSummary(
        voice_version_id=row.id,
        voice_id=row.voice_id,
        voice_name=voice_name,
        version=row.version,
        model_tag=row.model_tag,
        label=meta.get("label"),
        ref_text=row.ref_text,
        imported=bool(meta.get("imported")),
        created_at=row.created_at,
    )

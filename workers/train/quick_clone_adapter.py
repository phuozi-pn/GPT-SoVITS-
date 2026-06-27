"""Quick clone: prepare ref audio + text for api_v2 zero-shot (no GPU fine-tune)."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from uuid import UUID

from domains.assets.ref_text import align_ref_text_to_engine_ref
from voice_platform.config import get_db_session, get_settings
from voice_platform.engine.dataset_slice import wav_duration_sec
from voice_platform.engine.infer_weights import read_v2pro_base_weights
from voice_platform.engine.infer_defaults import default_infer_metadata, quick_clone_infer_metadata
from voice_platform.engine.paths import host_path_to_container
from voice_platform.engine.train_dataset import trim_wav_copy
from voice_platform.job.repository import VoiceVersionRepository
from voice_platform.job.schemas import MODEL_TAG_V2PRO, TrainPayload
from voice_platform.storage.resolve import resolve_storage_uri

logger = logging.getLogger(__name__)


class QuickCloneTrainAdapter:
    """Register a VoiceVersion using the user's uploaded audio as engine reference.

    Suitable for local dev without GPU fine-tune: ENGINE_MOCK=false + api_v2 /tts.
    """

    def run(self, *, payload: TrainPayload, owner_user_id: UUID, job_id: UUID) -> dict:
        settings = get_settings()
        if not payload.asset_urls:
            raise RuntimeError("Quick clone requires uploaded voice asset")

        src = resolve_storage_uri(payload.asset_urls[0])
        hyper = payload.hyperparams or {}
        ref_text = (hyper.get("ref_text") or settings.engine_train_sample_text).strip()
        if not ref_text:
            raise RuntimeError("ref_text required for quick clone")

        staging_dir = Path(settings.storage_root) / str(owner_user_id) / "quick_clone" / str(job_id)
        staging_dir.mkdir(parents=True, exist_ok=True)
        ref_out = staging_dir / "ref.wav"

        duration = wav_duration_sec(src)

        # Long uploads: zero-shot only needs 3–9s ref aligned with ref_text.
        # Slicing a full song then pairing random segments with one-line ref_text
        # makes the engine leak lyrics / garbled content into synthesis.
        if duration > 15.0:
            trim_wav_copy(src, ref_out, max_sec=9.0)
            logger.info(
                "quick_clone long asset %.1fs -> head ref %s (use ref_text matching audio start)",
                duration,
                ref_out.name,
            )
        else:
            trim_wav_copy(src, ref_out, max_sec=min(9.0, max(3.0, duration)))
            logger.info("quick_clone short asset %.1fs -> %s", duration, ref_out.name)

        ref_text_infer, ref_aligned = align_ref_text_to_engine_ref(
            ref_out,
            fallback=ref_text,
        )
        if ref_aligned and ref_text_infer != ref_text:
            logger.info(
                "quick_clone ref_text aligned to trimmed ref (was %d chars, now %d)",
                len(ref_text),
                len(ref_text_infer),
            )
        elif not ref_aligned:
            logger.warning(
                "quick_clone using upload ref_text without ASR realign; "
                "ensure text matches the first ~9s of audio exactly"
            )

        host_ref = str(ref_out.resolve())
        container_ref = host_path_to_container(host_ref)
        engine_root = (settings.engine_train_root or "").strip()
        if engine_root and Path(engine_root).is_dir():
            engine_ref_dir = Path(engine_root) / "quick_clone_refs"
            engine_ref_dir.mkdir(parents=True, exist_ok=True)
            engine_ref_file = engine_ref_dir / f"{job_id}.wav"
            shutil.copy2(ref_out, engine_ref_file)
            host_ref = str(engine_ref_file.resolve())
            root_in_docker = (
                settings.engine_train_root_in_docker or "/workspace/GPT-SoVITS"
            ).rstrip("/")
            container_ref = f"{root_in_docker}/quick_clone_refs/{job_id}.wav"
            logger.info("quick_clone engine ref %s -> %s", engine_ref_file, container_ref)

        base_gpt, base_sovits = None, None
        engine_root_path = Path(engine_root) if engine_root and Path(engine_root).is_dir() else None
        if engine_root_path:
            parsed = read_v2pro_base_weights(engine_root_path)
            if parsed:
                base_gpt, base_sovits = parsed

        session = get_db_session()
        try:
            versions = VoiceVersionRepository(session)
            row = versions.create_version(
                voice_id=payload.voice_id,
                owner_user_id=owner_user_id,
                model_tag=payload.model_tag,
                checkpoint_uri=f"quick://{payload.voice_id}/{job_id}",
                ref_audio_uri=payload.asset_urls[0],
                ref_text=ref_text_infer,
                metadata={
                    "train_job_id": str(job_id),
                    "train_mode": "quick_clone",
                    "mock": False,
                    "engine_use_base_weights": True,
                    "engine_ref_audio_path": host_ref,
                    "engine_ref_audio_container": container_ref,
                    "text_lang": settings.train_asr_language,
                    "prompt_lang": settings.train_asr_language,
                    "voice_asset_id": str(payload.voice_asset_id),
                    "consent_id": str(payload.consent_id),
                    "source_duration_sec": duration,
                    **quick_clone_infer_metadata(),
                    **(
                        {
                            "engine_gpt_weights": base_gpt,
                            "engine_sovits_weights": base_sovits,
                        }
                        if base_gpt and base_sovits
                        else {}
                    ),
                },
            )
            return {
                "voice_version_id": str(row.id),
                "checkpoint_uri": row.checkpoint_uri,
                "model_tag": row.model_tag or MODEL_TAG_V2PRO,
                "version": row.version,
                "train_mode": "quick_clone",
                "engine_ref_audio_path": host_ref,
            }
        finally:
            session.close()

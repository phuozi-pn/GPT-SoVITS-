"""Cloud GPU fine-tune: SSH orchestration + local weight import."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from uuid import UUID

from domains.assets.convert import ensure_wav
from domains.voices.weight_registration import EngineWeightsRegistration, register_engine_weights_version
from domains.cloud_train.service import resolve_ssh_config_for_user
from voice_platform.asr.service import AssetAsrService
from voice_platform.cloud_train.local_dataset import prepare_local_cloud_dataset
from voice_platform.cloud_train.orchestrator import CloudTrainOrchestrator
from voice_platform.cloud_train.remote_env import ensure_remote_train_environment
from voice_platform.cloud_train.ssh_client import CloudTrainError
from voice_platform.config import get_db_session, get_settings
from voice_platform.job.schemas import MODEL_TAG_V2PRO, TrainPayload
from voice_platform.storage.resolve import resolve_storage_uri

logger = logging.getLogger(__name__)


class CloudTrainAdapter:
    """Upload user audio to rented GPU, run train.sh, import weights locally."""

    def run(self, *, payload: TrainPayload, owner_user_id: UUID, job_id: UUID) -> dict:
        settings = get_settings()
        if not payload.asset_urls:
            raise CloudTrainError("Cloud train requires uploaded voice asset")

        engine_root = (settings.engine_train_root or "").strip()
        if not engine_root or not Path(engine_root).is_dir():
            raise CloudTrainError(
                "CLOUD_TRAIN requires ENGINE_TRAIN_ROOT pointing at local GPT-SoVITS clone "
                "to install pulled weights for synthesis"
            )

        src = resolve_storage_uri(payload.asset_urls[0])
        wav = ensure_wav(src)

        hyper = payload.hyperparams or {}
        ref_text = (hyper.get("ref_text") or settings.engine_train_sample_text).strip()
        if not ref_text:
            raise CloudTrainError("ref_text required for cloud train (ASR or manual)")

        work = Path(settings.storage_root) / "cloud_train" / str(job_id)
        prepared = None
        infer_ref_text = ref_text

        local_prep = hyper.get("cloud_local_dataset_prep")
        if local_prep is None:
            local_prep = settings.cloud_train_local_dataset_prep
        else:
            local_prep = bool(local_prep)

        use_asr_opt = hyper.get("cloud_use_asr")
        asr = AssetAsrService(settings)
        if use_asr_opt is None:
            use_asr = settings.train_use_asr and asr.is_available()
        else:
            use_asr = bool(use_asr_opt) and asr.is_available()

        session = get_db_session()
        try:
            ssh_config = resolve_ssh_config_for_user(session, owner_user_id)
        finally:
            session.close()

        remote_env = ensure_remote_train_environment(
            ssh_config,
            local_dataset_prep=local_prep,
        )
        logger.info(
            "cloud_train remote env synced python=%s torch=%s",
            remote_env.python,
            remote_env.torch_version,
        )

        if local_prep:
            dataset_dir = work / "dataset"
            try:
                prepared = prepare_local_cloud_dataset(
                    wav_path=wav,
                    out_dir=dataset_dir,
                    ref_text=ref_text,
                    language=settings.train_asr_language,
                    use_asr=use_asr,
                    use_llm_enrich=hyper.get("cloud_llm_enrich"),
                    settings=settings,
                )
                infer_ref_text = prepared.infer_ref_text
                logger.info(
                    "cloud_train local dataset prep mode=%s segments=%s local_prep=%s use_asr=%s",
                    prepared.mode,
                    prepared.segment_count,
                    local_prep,
                    use_asr,
                )
            except Exception as exc:
                logger.warning(
                    "local dataset prep failed, falling back to remote prepare: %s",
                    exc,
                )
                prepared = None
                if remote_env.checks:
                    remote_env = ensure_remote_train_environment(
                        ssh_config,
                        local_dataset_prep=False,
                    )

        session = get_db_session()
        try:
            outcome = CloudTrainOrchestrator(
                ssh_config,
                storage_root=settings.storage_root,
            ).run(
                local_wav=wav,
                job_id=str(job_id),
                prepared_dataset=prepared,
                remote_env=remote_env,
            )
        finally:
            session.close()

        result = outcome.result
        gpt_rel = str(result["gpt_checkpoint"]).replace("\\", "/")
        sovits_rel = str(result["sovits_checkpoint"]).replace("\\", "/")
        if outcome.infer_ref_text:
            infer_ref_text = outcome.infer_ref_text.strip()

        root = Path(engine_root)
        gpt_dst = root / gpt_rel
        sovits_dst = root / sovits_rel
        gpt_dst.parent.mkdir(parents=True, exist_ok=True)
        sovits_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(outcome.gpt_local, gpt_dst)
        shutil.copy2(outcome.sovits_local, sovits_dst)

        session = get_db_session()
        try:
            row = register_engine_weights_version(
                session=session,
                reg=EngineWeightsRegistration(
                    voice_id=payload.voice_id,
                    owner_user_id=owner_user_id,
                    gpt_rel=gpt_rel,
                    sovits_rel=sovits_rel,
                    ref_src_path=outcome.ref_wav_local,
                    ref_text=infer_ref_text,
                    model_tag=payload.model_tag or MODEL_TAG_V2PRO,
                    label=f"cloud-{result.get('exp_name', job_id.hex[:8])}",
                    ref_name_prefix="cloud_ref",
                    text_lang=settings.train_asr_language or "zh",
                    extra_metadata={
                        "train_mode": "cloud",
                        "train_job_id": str(job_id),
                        "cloud_exp_name": result.get("exp_name"),
                        "cloud_elapsed_sec": result.get("elapsed_sec"),
                        "gpt_epochs": result.get("gpt_epochs"),
                        "sovits_epochs": result.get("sovits_epochs"),
                        "cloud_dataset_mode": outcome.dataset_mode or "remote",
                        "cloud_dataset_segments": prepared.segment_count if prepared else None,
                        "voice_asset_id": str(payload.voice_asset_id),
                        "consent_id": str(payload.consent_id),
                    },
                ),
            )
            logger.info(
                "cloud_train imported voice_version=%s gpt=%s sovits=%s",
                row.id,
                gpt_rel,
                sovits_rel,
            )
            return {
                "voice_version_id": str(row.id),
                "checkpoint_uri": row.checkpoint_uri,
                "model_tag": row.model_tag or MODEL_TAG_V2PRO,
                "version": row.version,
                "train_mode": "cloud",
                "engine_gpt_weights": gpt_rel,
                "engine_sovits_weights": sovits_rel,
                "gpt_epochs": result.get("gpt_epochs"),
                "sovits_epochs": result.get("sovits_epochs"),
                "elapsed_sec": result.get("elapsed_sec"),
                "cloud_dataset_segments": outcome.segment_count if outcome.segment_count is not None else (prepared.segment_count if prepared else None),
                "cloud_dataset_mode": outcome.dataset_mode,
                "cloud_remote_work_dir": outcome.remote_work_dir,
                "cloud_remote_dataset_dir": outcome.remote_dataset_dir,
            }
        finally:
            session.close()

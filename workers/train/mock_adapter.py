"""Placeholder train adapter (no GPU)."""

from __future__ import annotations

from uuid import UUID

from voice_platform.config import get_db_session
from voice_platform.job.repository import VoiceVersionRepository
from voice_platform.job.schemas import MODEL_TAG_V2PRO, TrainPayload


class MockTrainAdapter:
    """Creates VoiceVersion with placeholder checkpoint (no GPU fine-tune)."""

    def run(self, *, payload: TrainPayload, owner_user_id: UUID, job_id: UUID) -> dict:
        session = get_db_session()
        try:
            versions = VoiceVersionRepository(session)
            row = versions.create_version(
                voice_id=payload.voice_id,
                owner_user_id=owner_user_id,
                model_tag=payload.model_tag,
                checkpoint_uri=f"local://checkpoints/{payload.voice_id}/mock-{job_id}.ckpt",
                ref_audio_uri=payload.asset_urls[0] if payload.asset_urls else None,
                metadata={
                    "train_job_id": str(job_id),
                    "train_mode": "mock",
                    "mock": True,
                    "voice_asset_id": str(payload.voice_asset_id),
                    "consent_id": str(payload.consent_id),
                },
            )
            return {
                "voice_version_id": str(row.id),
                "checkpoint_uri": row.checkpoint_uri,
                "model_tag": row.model_tag or MODEL_TAG_V2PRO,
                "version": row.version,
                "train_mode": "mock",
            }
        finally:
            session.close()

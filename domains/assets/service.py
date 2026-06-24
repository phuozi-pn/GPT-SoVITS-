from __future__ import annotations

from pathlib import Path
from uuid import UUID

from domains.assets.errors import AssetQcError
from domains.assets.qc import run_qc
from domains.assets.ref_text import resolve_upload_ref_text
from voice_platform.config import get_settings
from voice_platform.job.repository import VoiceRepository
from voice_platform.job.schemas import (
    AssetConfirmResponse,
    AssetQcResponse,
    AssetUploadResponse,
    QcResult,
)
from voice_platform.storage.local import LocalStorage


class AssetService:
    def __init__(self, session) -> None:
        self._voices = VoiceRepository(session)
        self._storage = LocalStorage()

    def upload(
        self,
        *,
        owner_user_id: UUID,
        voice_id: UUID,
        filename: str,
        data: bytes,
        ref_text: str | None = None,
    ) -> AssetUploadResponse:
        settings = get_settings()
        if len(data) > settings.asset_max_bytes:
            raise AssetQcError(
                "FILE_TOO_LARGE",
                f"File exceeds {settings.asset_max_bytes} bytes",
            )

        if not self._voices.user_owns_voice(voice_id, owner_user_id):
            raise AssetQcError("FORBIDDEN", "Voice not accessible")

        consent = self._voices.default_consent_for_voice(voice_id)
        if consent is None or consent.status != "approved":
            raise AssetQcError("CONSENT_REQUIRED", "Approved consent required before upload")

        ext = Path(filename).suffix.lower().lstrip(".") or "wav"
        asset = self._voices.create_asset(
            voice_id=voice_id,
            owner_user_id=owner_user_id,
            storage_uri="pending",
        )
        storage_uri, abs_path = self._storage.save_training_asset(
            user_id=owner_user_id,
            asset_id=asset.id,
            data=data,
            ext=ext,
        )

        abs_file = Path(abs_path)
        try:
            qc = run_qc(path=abs_file, filename=filename, ref_text=None)
        except AssetQcError:
            self._voices.delete_asset(asset.id)
            abs_file.unlink(missing_ok=True)
            abs_file.with_suffix(".wav").unlink(missing_ok=True)
            raise

        wav_path = abs_file.with_suffix(".wav")
        if not wav_path.is_file():
            wav_path = abs_file

        resolved_ref, ref_auto, asr_provider, asr_issues = resolve_upload_ref_text(
            wav_path,
            ref_text,
            settings=settings,
        )
        qc = qc.model_copy(
            update={
                "ref_text": resolved_ref,
                "ref_text_auto": ref_auto,
                "asr_provider": asr_provider,
                "issues": [*qc.issues, *asr_issues],
            }
        )

        if wav_path.is_file() and wav_path.resolve() != abs_file.resolve():
            storage_uri = f"local://{Path(str(owner_user_id)) / 'training' / f'{asset.id}.wav'}"

        qc_passed = qc.status == "passed"
        updated = self._voices.update_asset_qc(
            asset_id=asset.id,
            storage_uri=storage_uri,
            qc_passed=qc_passed,
            qc_result=qc.model_dump(mode="json"),
        )
        assert updated is not None

        return AssetUploadResponse(
            asset_id=updated.id,
            voice_id=voice_id,
            storage_uri=storage_uri,
            qc_passed=qc_passed,
            qc_result=qc,
        )

    def get_qc(self, *, owner_user_id: UUID, asset_id: UUID) -> AssetQcResponse:
        asset = self._voices.get_asset(asset_id)
        if asset is None or asset.owner_user_id != owner_user_id:
            raise AssetQcError("FORBIDDEN", "Asset not accessible")

        qc_result = None
        if asset.qc_result_json:
            qc_result = QcResult.model_validate(asset.qc_result_json)

        return AssetQcResponse(
            asset_id=asset.id,
            voice_id=asset.voice_id,
            locked=asset.locked,
            qc_passed=asset.qc_passed,
            qc_result=qc_result,
        )

    def confirm(self, *, owner_user_id: UUID, asset_id: UUID) -> AssetConfirmResponse:
        asset = self._voices.get_asset(asset_id)
        if asset is None or asset.owner_user_id != owner_user_id:
            raise AssetQcError("FORBIDDEN", "Asset not accessible")
        if asset.locked:
            raise AssetQcError("ASSET_LOCKED", "Asset already locked")
        if not asset.qc_passed:
            raise AssetQcError("QC_NOT_PASSED", "QC must pass before confirm")

        locked = self._voices.lock_asset(asset_id)
        assert locked is not None
        return AssetConfirmResponse(
            asset_id=locked.id,
            voice_id=locked.voice_id,
            locked=True,
        )

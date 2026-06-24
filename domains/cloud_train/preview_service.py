from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID

from domains.assets.convert import ensure_wav
from voice_platform.asr.service import AssetAsrService
from voice_platform.cloud_train.local_dataset import prepare_local_cloud_dataset
from voice_platform.config import get_settings
from voice_platform.engine.dataset_slice import wav_duration_sec
from voice_platform.job.repository import VoiceRepository
from voice_platform.storage.local import LocalStorage
from voice_platform.storage.resolve import resolve_storage_uri


class DatasetPreviewError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class CloudDatasetPreviewService:
    def __init__(self, session) -> None:
        self._session = session
        self._voices = VoiceRepository(session)
        self._storage = LocalStorage()

    def preview(
        self,
        *,
        owner_user_id: UUID,
        asset_id: UUID,
        use_asr: bool | None = None,
        use_llm_enrich: bool | None = None,
    ) -> dict:
        asset = self._voices.get_asset(asset_id)
        if asset is None or asset.owner_user_id != owner_user_id:
            raise DatasetPreviewError("ASSET_NOT_FOUND", "素材不存在或无权访问", 404)
        if not asset.locked:
            raise DatasetPreviewError("ASSET_NOT_LOCKED", "请先完成步骤 ② 上传并锁定素材", 400)
        if not asset.qc_passed:
            raise DatasetPreviewError("QC_FAILED", "素材未通过质检，无法预览切分", 422)

        qc = asset.qc_result_json or {}
        ref_text = (qc.get("ref_text") or "").strip()
        if not ref_text:
            raise DatasetPreviewError("REF_TEXT_MISSING", "缺少参考文本，请重新上传或填写参考文本", 400)

        settings = get_settings()
        wav = ensure_wav(resolve_storage_uri(asset.storage_uri))
        source_duration = wav_duration_sec(wav)

        asr = AssetAsrService(settings)
        if use_asr is None:
            use_asr = settings.train_use_asr and asr.is_available()
        else:
            use_asr = bool(use_asr) and asr.is_available()

        preview_root = Path(settings.storage_root) / str(owner_user_id) / "previews" / str(asset_id)
        if preview_root.exists():
            shutil.rmtree(preview_root, ignore_errors=True)
        dataset_dir = preview_root / "dataset"
        prepared = prepare_local_cloud_dataset(
            wav_path=wav,
            out_dir=dataset_dir,
            ref_text=ref_text,
            language=settings.train_asr_language,
            use_asr=use_asr,
            use_llm_enrich=use_llm_enrich,
            settings=settings,
        )

        meta_by_index = {m.get("index", i): m for i, m in enumerate(prepared.segment_meta)}
        pub_segments = preview_root / "segments"
        pub_segments.mkdir(parents=True, exist_ok=True)
        segments_out: list[dict] = []
        for i, (seg_path, text) in enumerate(prepared.pairs):
            src = Path(seg_path)
            dst = pub_segments / src.name
            shutil.copy2(src, dst)
            rel = f"{owner_user_id}/previews/{asset_id}/segments/{dst.name}"
            meta = meta_by_index.get(i, {})
            seg_out: dict = {
                "index": i,
                "name": dst.name,
                "duration_sec": round(wav_duration_sec(dst), 2),
                "text": text,
                "audio_url": f"/files/{rel}",
            }
            if meta:
                seg_out["text_original"] = meta.get("text_original") or text
                seg_out["emotion"] = meta.get("emotion")
                seg_out["emotion_label"] = meta.get("emotion_label")
                seg_out["emotion_strength"] = meta.get("emotion_strength")
                if meta.get("notes"):
                    seg_out["notes"] = meta.get("notes")
            segments_out.append(seg_out)

        return {
            "asset_id": str(asset_id),
            "source_duration_sec": round(source_duration, 2),
            "mode": prepared.mode,
            "segment_count": prepared.segment_count,
            "use_asr": use_asr,
            "segments": segments_out,
            "infer_ref_text": prepared.infer_ref_text,
            "enrich_mode": prepared.enrich_mode,
        }

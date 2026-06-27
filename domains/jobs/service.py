from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from domains.cloud_train.progress import read_cloud_train_progress
from voice_platform.config import get_settings
from voice_platform.job.models import VoiceRow, VoiceVersionRow
from voice_platform.job.repository import JobRepository
from voice_platform.job.schemas import (
    JobRecord,
    JobResponse,
    JobStatus,
    JobType,
    SynthesisHistoryDetail,
    SynthesisHistoryItem,
    SynthesisHistorySegment,
)
from voice_platform.storage.local import LocalStorage
from sqlalchemy import select


class JobService:
    """Domain service for admin job list & stats — wraps JobRepository."""

    def __init__(self, session) -> None:
        self._repo = JobRepository(session)
        self._session = session

    def list_recent(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        owner_user_id: UUID | None = None,
        limit: int = 50,
    ):
        return self._repo.list_recent(
            status=status,
            job_type=job_type,
            owner_user_id=owner_user_id,
            limit=limit,
        )

    def count_by_status(self, status: str) -> int:
        return self._repo.count_by_status(status)

    def count_failed_since(self, *, hours: int = 24) -> int:
        return self._repo.count_failed_since(hours=hours)

    def get_job_for_user(self, job_id: UUID, user_id: UUID) -> JobRecord | None:
        record = self._repo.get_job(job_id)
        if not record or record.owner_user_id != user_id:
            return None
        return record

    def list_synthesis_history(
        self,
        *,
        user_id: UUID,
        limit: int = 50,
        status: str | None = None,
    ) -> list[SynthesisHistoryItem]:
        fetch_limit = min(max(limit * 4, limit), 400)
        records = self._repo.list_recent(
            job_type=JobType.SYNTHESIZE.value,
            owner_user_id=user_id,
            status=status,
            limit=fetch_limit,
        )
        visible = [r for r in records if is_displayable_synthesis_history(r)][:limit]
        voice_map = self._voice_labels_for_records(visible)
        return [record_to_history_item(record, voice_map) for record in visible]

    def purge_empty_synthesis_history(self, *, user_id: UUID) -> int:
        """Delete failed synthesize jobs and succeeded jobs without audio for one user."""
        return self._repo.delete_non_displayable_synthesis_jobs(owner_user_id=user_id)

    def get_synthesis_detail(self, job_id: UUID, user_id: UUID) -> SynthesisHistoryDetail | None:
        record = self.get_job_for_user(job_id, user_id)
        if not record or record.job_type != JobType.SYNTHESIZE:
            return None
        voice_map = self._voice_labels_for_records([record])
        return record_to_history_detail(record, voice_map)

    def voice_labels_for_record(self, record: JobRecord) -> dict[UUID, tuple[str, str]]:
        return self._voice_labels_for_records([record])

    def _voice_labels_for_records(self, records: list[JobRecord]) -> dict[UUID, tuple[str, str]]:
        version_ids: set[UUID] = set()
        for record in records:
            vid = _primary_voice_version_id(record.payload)
            if vid:
                version_ids.add(vid)
            for seg in record.payload.get("segments") or []:
                raw = seg.get("voice_version_id")
                if raw:
                    try:
                        version_ids.add(UUID(str(raw)))
                    except ValueError:
                        pass
        if not version_ids:
            return {}
        rows = self._session.execute(
            select(VoiceVersionRow, VoiceRow)
            .join(VoiceRow, VoiceRow.id == VoiceVersionRow.voice_id)
            .where(VoiceVersionRow.id.in_(list(version_ids)))
        ).all()
        out: dict[UUID, tuple[str, str]] = {}
        for version, voice in rows:
            label = (version.metadata_json or {}).get("label") or ""
            out[version.id] = (voice.name, label)
        return out

    def resolve_export_download(
        self, *, job_id: UUID, user_id: UUID
    ) -> tuple[str, str, str]:
        """Resolve export download details for a completed job.

        Returns (absolute_path, filename, media_type).

        Raises JobExportError on any invalid state.
        """
        settings = get_settings()
        if not settings.compliance_export_required:
            raise JobExportError("LABEL_REQUIRED", "Compliant export is required", 403)

        record = self.get_job_for_user(job_id, user_id)
        if not record:
            raise JobExportError("JOB_NOT_FOUND", "Job not found", 404)
        if record.status != JobStatus.SUCCEEDED or not record.result:
            raise JobExportError("EXPORT_NOT_READY", "Job not completed successfully", 409)

        if record.job_type == JobType.SYNTHESIZE:
            if not record.result.get("export_compliant"):
                raise JobExportError("LABEL_REQUIRED", "Export is not compliance-labeled", 403)
            url = record.result.get("audio_url")
            filename = f"synthesis_{job_id}.wav"
        elif record.job_type == JobType.BATCH:
            if not record.result.get("zip_url"):
                raise JobExportError("EXPORT_NOT_FOUND", "Batch ZIP not available", 404)
            url = record.result["zip_url"]
            filename = f"batch_{job_id}.zip"
        else:
            raise JobExportError(
                "EXPORT_UNSUPPORTED", "Job type does not support export download", 400
            )

        rel = _rel_from_public_url(str(url))
        if not rel:
            raise JobExportError("EXPORT_PATH_INVALID", "Invalid export URL", 500)

        storage = LocalStorage()
        path = Path(storage.absolute_path(rel))
        if not path.is_file():
            raise JobExportError("EXPORT_FILE_MISSING", "Export file not found on disk", 404)

        media = "application/zip" if path.suffix == ".zip" else "audio/wav"
        return str(path), filename, media


class JobExportError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def get_job_for_user(session, job_id: UUID, user_id: UUID) -> JobRecord | None:
    """Deprecated: use JobService.get_job_for_user instead."""
    return JobService(session).get_job_for_user(job_id, user_id)


def is_displayable_synthesis_history(record: JobRecord) -> bool:
    """User-facing history only includes successful syntheses with playable audio."""
    return (
        record.status == JobStatus.SUCCEEDED
        and bool(record.result and record.result.get("audio_url"))
    )


def _rel_from_public_url(url: str) -> str | None:
    marker = "/files/"
    if marker not in url:
        return None
    return url.split(marker, 1)[1]


def record_to_response(record: JobRecord, voice_map: dict[UUID, tuple[str, str]] | None = None) -> JobResponse:
    resp = JobResponse(
        job_id=record.job_id,
        job_type=record.job_type,
        status=record.status,
        trace_id=record.trace_id,
        owner_user_id=record.owner_user_id,
        queue_position=record.queue_position,
        error_message=record.error_message,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
    if record.job_type == JobType.SYNTHESIZE:
        preview, full_text, segments = _extract_synthesis_text(record.payload)
        resp.text_preview = preview
        resp.full_text = full_text
        resp.segments = segments
        vid = _primary_voice_version_id(record.payload)
        if vid and voice_map and vid in voice_map:
            name, label = voice_map[vid]
            resp.voice_name = name
            resp.voice_version_label = label
        elif vid and voice_map is None:
            pass
    if record.result:
        if record.job_type == JobType.SYNTHESIZE:
            resp.audio_url = record.result.get("audio_url")
            resp.duration_sec = record.result.get("duration_sec")
            resp.chars_billed = record.result.get("chars_billed")
        elif record.job_type == JobType.TRAIN:
            vv = record.result.get("voice_version_id")
            resp.voice_version_id = UUID(vv) if vv else None
            resp.checkpoint_uri = record.result.get("checkpoint_uri")
            resp.model_tag = record.result.get("model_tag")
            gpt_e = record.result.get("gpt_epochs")
            sov_e = record.result.get("sovits_epochs")
            elapsed = record.result.get("elapsed_sec")
            segs = record.result.get("cloud_dataset_segments")
            remote_work = record.result.get("cloud_remote_work_dir")
            remote_dataset = record.result.get("cloud_remote_dataset_dir")
            if gpt_e is not None:
                resp.train_gpt_epochs = int(gpt_e)
            if sov_e is not None:
                resp.train_sovits_epochs = int(sov_e)
            if elapsed is not None:
                resp.train_elapsed_sec = float(elapsed)
            if segs is not None:
                resp.train_dataset_segments = int(segs)
            if remote_work:
                resp.train_remote_work_dir = str(remote_work)
            if remote_dataset:
                resp.train_remote_dataset_path = str(remote_dataset)
        elif record.job_type == JobType.BATCH:
            resp.line_count = record.result.get("line_count")
            resp.succeeded_count = record.result.get("succeeded_count")
            resp.failed_count = record.result.get("failed_count")
            resp.zip_url = record.result.get("zip_url")
    if record.job_type == JobType.TRAIN and record.status in (JobStatus.RUNNING, JobStatus.QUEUED):
        settings = get_settings()
        prog = read_cloud_train_progress(storage_root=settings.storage_root, job_id=record.job_id)
        if prog:
            resp.train_progress_phase = str(prog.get("phase") or "") or None
            resp.train_progress_message = str(prog.get("message") or "") or None
            if prog.get("gpt_epochs") is not None and resp.train_gpt_epochs is None:
                resp.train_gpt_epochs = int(prog["gpt_epochs"])
            if prog.get("sovits_epochs") is not None and resp.train_sovits_epochs is None:
                resp.train_sovits_epochs = int(prog["sovits_epochs"])
            if prog.get("segment_count") is not None and resp.train_dataset_segments is None:
                resp.train_dataset_segments = int(prog["segment_count"])
            if prog.get("remote_work_dir") and not resp.train_remote_work_dir:
                resp.train_remote_work_dir = str(prog["remote_work_dir"])
            if prog.get("remote_dataset_dir") and not resp.train_remote_dataset_path:
                resp.train_remote_dataset_path = str(prog["remote_dataset_dir"])
    return resp


def record_to_history_item(
    record: JobRecord,
    voice_map: dict[UUID, tuple[str, str]],
) -> SynthesisHistoryItem:
    preview, _, _ = _extract_synthesis_text(record.payload)
    vid = _primary_voice_version_id(record.payload)
    voice_name = voice_version_label = None
    if vid and vid in voice_map:
        voice_name, voice_version_label = voice_map[vid]
    audio_url = duration_sec = chars_billed = None
    if record.result:
        audio_url = record.result.get("audio_url")
        duration_sec = record.result.get("duration_sec")
        chars_billed = record.result.get("chars_billed")
    return SynthesisHistoryItem(
        job_id=record.job_id,
        status=record.status,
        created_at=record.created_at,
        text_preview=preview,
        voice_name=voice_name,
        voice_version_label=voice_version_label or None,
        audio_url=audio_url,
        duration_sec=duration_sec,
        chars_billed=chars_billed,
        error_message=record.error_message,
    )


def record_to_history_detail(
    record: JobRecord,
    voice_map: dict[UUID, tuple[str, str]],
) -> SynthesisHistoryDetail:
    item = record_to_history_item(record, voice_map)
    _, full_text, segments = _extract_synthesis_text(record.payload, voice_map=voice_map)
    return SynthesisHistoryDetail(
        **item.model_dump(),
        full_text=full_text,
        segments=segments,
        updated_at=record.updated_at,
    )


def _primary_voice_version_id(payload: dict[str, Any]) -> UUID | None:
    segments = payload.get("segments") or []
    if segments:
        raw = segments[0].get("voice_version_id")
        if raw:
            try:
                return UUID(str(raw))
            except ValueError:
                return None
    raw = payload.get("voice_version_id")
    if raw:
        try:
            return UUID(str(raw))
        except ValueError:
            return None
    return None


def _extract_synthesis_text(
    payload: dict[str, Any],
    *,
    voice_map: dict[UUID, tuple[str, str]] | None = None,
) -> tuple[str, str, list[SynthesisHistorySegment]]:
    segments_out: list[SynthesisHistorySegment] = []
    if payload.get("segments"):
        texts: list[str] = []
        for seg in payload["segments"]:
            text = str(seg.get("text") or "").strip()
            if not text:
                continue
            texts.append(text)
            vid_raw = seg.get("voice_version_id")
            vid = None
            voice_name = None
            if vid_raw:
                try:
                    vid = UUID(str(vid_raw))
                    if voice_map and vid in voice_map:
                        voice_name = voice_map[vid][0]
                except ValueError:
                    vid = None
            segments_out.append(
                SynthesisHistorySegment(
                    voice_version_id=vid,
                    voice_name=voice_name,
                    text=text,
                    role=seg.get("role"),
                )
            )
        full = "\n\n".join(texts)
        preview = full[:120]
        return preview, full, segments_out
    text = str(payload.get("text") or "").strip()
    preview = text[:120]
    vid = _primary_voice_version_id(payload)
    voice_name = voice_map.get(vid)[0] if voice_map and vid and vid in voice_map else None
    if text:
        segments_out = [
            SynthesisHistorySegment(voice_version_id=vid, voice_name=voice_name, text=text)
        ]
    return preview, text, segments_out

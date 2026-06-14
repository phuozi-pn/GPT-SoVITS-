from __future__ import annotations

from pathlib import Path
from uuid import UUID

from apps.api.deps import get_current_user_id
from domains.jobs.service import get_job_for_user
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from voice_platform.config import get_db_session, get_settings
from voice_platform.job.schemas import JobStatus, JobType
from voice_platform.storage.local import LocalStorage

router = APIRouter()


def get_session():
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


def _rel_from_public_url(url: str) -> str | None:
    marker = "/files/"
    if marker not in url:
        return None
    return url.split(marker, 1)[1]


@router.get("/exports/{job_id}/download")
def download_compliant_export(
    job_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    """Download compliant-labeled audio or ZIP (REQ-010). Raw unlabeled files are not exposed."""
    settings = get_settings()
    if not settings.compliance_export_required:
        raise HTTPException(
            status_code=403,
            detail={"code": "LABEL_REQUIRED", "message": "Compliant export is required"},
        )

    record = get_job_for_user(session, job_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "Job not found"})
    if record.status != JobStatus.SUCCEEDED or not record.result:
        raise HTTPException(
            status_code=409,
            detail={"code": "EXPORT_NOT_READY", "message": "Job not completed successfully"},
        )

    if record.job_type == JobType.SYNTHESIZE:
        if not record.result.get("export_compliant"):
            raise HTTPException(
                status_code=403,
                detail={"code": "LABEL_REQUIRED", "message": "Export is not compliance-labeled"},
            )
        url = record.result.get("audio_url")
        filename = f"synthesis_{job_id}.wav"
    elif record.job_type == JobType.BATCH:
        if not record.result.get("zip_url"):
            raise HTTPException(
                status_code=404,
                detail={"code": "EXPORT_NOT_FOUND", "message": "Batch ZIP not available"},
            )
        url = record.result["zip_url"]
        filename = f"batch_{job_id}.zip"
    else:
        raise HTTPException(
            status_code=400,
            detail={"code": "EXPORT_UNSUPPORTED", "message": "Job type does not support export download"},
        )

    rel = _rel_from_public_url(str(url))
    if not rel:
        raise HTTPException(
            status_code=500,
            detail={"code": "EXPORT_PATH_INVALID", "message": "Invalid export URL"},
        )

    storage = LocalStorage()
    path = Path(storage.absolute_path(rel))
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail={"code": "EXPORT_FILE_MISSING", "message": "Export file not found on disk"},
        )

    media = "application/zip" if path.suffix == ".zip" else "audio/wav"
    return FileResponse(
        path,
        media_type=media,
        filename=filename,
        headers={"X-AI-Generated": "true", "X-Export-Compliant": "true"},
    )

from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session
from apps.api.exceptions import raise_domain_http
from domains.jobs.service import JobExportError, JobService
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/exports/{job_id}/download")
def download_compliant_export(
    job_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    """Download compliant-labeled audio or ZIP (REQ-010). Raw unlabeled files are not exposed."""
    try:
        path, filename, media = JobService(session).resolve_export_download(
            job_id=job_id, user_id=user_id
        )
    except JobExportError as exc:
        raise_domain_http(exc)

    return FileResponse(
        path,
        media_type=media,
        filename=filename,
        headers={"X-AI-Generated": "true", "X-Export-Compliant": "true"},
    )

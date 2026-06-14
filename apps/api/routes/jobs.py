from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id
from domains.jobs.service import get_job_for_user, record_to_response
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from voice_platform.config import get_db_session
from voice_platform.job.schemas import JobResponse

router = APIRouter()


def get_session():
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> JobResponse:
    record = get_job_for_user(session, job_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "Job not found"})
    return record_to_response(record)

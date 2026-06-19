from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.deps import get_session, require_admin_user
from domains.jobs.service import JobService, record_to_response
from voice_platform.job.schemas import JobResponse, JobStatus, JobType

router = APIRouter()


class AdminJobListResponse(BaseModel):
    items: list[JobResponse]
    total: int


@router.get("/admin/jobs", response_model=AdminJobListResponse)
def list_admin_jobs(
  status: JobStatus | None = Query(default=None, description="Filter by job status"),
  job_type: JobType | None = Query(default=None, description="Filter by job type"),
  owner: UUID | None = Query(default=None, description="Filter by owner user id"),
  limit: int = Query(default=50, ge=1, le=200),
  _: UUID = Depends(require_admin_user),
  session: Session = Depends(get_session),
) -> AdminJobListResponse:
    """Read-only job list for operators (failed/running triage). Requires admin user."""
    svc = JobService(session)
    records = svc.list_recent(
        status=status.value if status else None,
        job_type=job_type.value if job_type else None,
        owner_user_id=owner,
        limit=limit,
    )
    items = [record_to_response(r) for r in records]
    return AdminJobListResponse(items=items, total=len(items))


class PlatformStatsResponse(BaseModel):
    release: str
    jobs_queued: int = 0
    jobs_running: int = 0
    jobs_failed_24h: int = 0


@router.get("/admin/stats", response_model=PlatformStatsResponse)
def platform_stats(
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> PlatformStatsResponse:
    from apps.api.config import get_settings

    svc = JobService(session)
    return PlatformStatsResponse(
        release=get_settings().platform_release_version,
        jobs_queued=svc.count_by_status(JobStatus.QUEUED.value),
        jobs_running=svc.count_by_status(JobStatus.RUNNING.value),
        jobs_failed_24h=svc.count_failed_since(hours=24),
    )

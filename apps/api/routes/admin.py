from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.deps import get_session, require_admin_user
from apps.api.exceptions import raise_domain_http
from domains.jobs.service import JobService, record_to_response
from domains.quota.service import QuotaService, QuotaServiceError
from voice_platform.job.schemas import JobResponse, JobStatus, JobType
from voice_platform.quota.schemas import QuotaSummary, UserUsageReportRow

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


class UserUsageReportResponse(BaseModel):
    billing_month: str
    items: list[UserUsageReportRow]
    total: int


@router.get("/admin/usage-report", response_model=UserUsageReportResponse)
def user_usage_report(
    billing_month: str | None = Query(default=None, description="YYYY-MM, default current month"),
    limit: int = Query(default=100, ge=1, le=500),
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> UserUsageReportResponse:
    from voice_platform.quota.period import current_billing_month

    month = billing_month or current_billing_month()
    items = QuotaService(session).list_usage_report(billing_month=month, limit=limit)
    return UserUsageReportResponse(billing_month=month, items=items, total=len(items))


class AdminUserQuotaRequest(BaseModel):
    monthly_char_limit: int | None = Field(default=None, ge=0, le=10_000_000)
    monthly_train_limit: int | None = Field(default=None, ge=0, le=1000)


@router.patch("/admin/users/{user_id}/quota", response_model=QuotaSummary)
def set_user_quota_limits(
    user_id: UUID,
    body: AdminUserQuotaRequest,
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> QuotaSummary:
    """运营为指定用户设置月度合成/训练配额上限（留空字段不修改）。"""
    if body.monthly_char_limit is None and body.monthly_train_limit is None:
        return QuotaService(session).get_summary(user_id)
    try:
        return QuotaService(session).set_user_limits(
            user_id,
            monthly_char_limit=body.monthly_char_limit,
            monthly_train_limit=body.monthly_train_limit,
        )
    except QuotaServiceError as exc:
        raise_domain_http(exc)


class AvatarBackfillResponse(BaseModel):
    covers_assigned: int
    covers_relinked: int
    avatars_assigned: int
    owners_touched: int


@router.post("/admin/avatars/backfill", response_model=AvatarBackfillResponse)
def backfill_avatars(
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> AvatarBackfillResponse:
    """为缺封面/头像的音色馆条目与创作者写入默认插画 URL。"""
    from domains.marketplace.avatar_assign import AvatarAssignService

    result = AvatarAssignService(session).backfill_all()
    return AvatarBackfillResponse(
        covers_assigned=result.covers_assigned,
        covers_relinked=result.covers_relinked,
        avatars_assigned=result.avatars_assigned,
        owners_touched=result.owners_touched,
    )

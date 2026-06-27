from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session
from domains.jobs.service import JobService, get_job_for_user, record_to_response
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from voice_platform.job.repository import BatchLineRepository
from voice_platform.job.schemas import (
    BatchLineRetryRequest,
    BatchLinesResponse,
    JobResponse,
    SynthesisHistoryDetail,
    SynthesisHistoryItem,
)
from voice_platform.job.queue import RedisJobQueue

router = APIRouter()


@router.get("/jobs", response_model=list[SynthesisHistoryItem])
def list_synthesis_jobs(
    user_id: UUID = Depends(get_current_user_id),
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[SynthesisHistoryItem]:
    """当前用户的合成历史列表（按创建时间倒序）。"""
    return JobService(session).list_synthesis_history(user_id=user_id, limit=limit, status=status)


@router.get("/jobs/{job_id}/detail", response_model=SynthesisHistoryDetail)
def get_synthesis_history_detail(
    job_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> SynthesisHistoryDetail:
    detail = JobService(session).get_synthesis_detail(job_id, user_id)
    if not detail:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "Job not found"})
    return detail


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> JobResponse:
    svc = JobService(session)
    record = get_job_for_user(session, job_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "Job not found"})
    voice_map = svc.voice_labels_for_record(record) if record.job_type.value == "synthesize" else None
    return record_to_response(record, voice_map)


@router.get("/jobs/{job_id}/lines", response_model=BatchLinesResponse)
def get_batch_lines(
    job_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> BatchLinesResponse:
    """获取批量合成 Job 的逐行状态（实时进度）。"""
    record = get_job_for_user(session, job_id, user_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": "Job not found"},
        )
    if record.job_type.value != "batch":
        raise HTTPException(
            status_code=400,
            detail={"code": "NOT_BATCH_JOB", "message": "This endpoint is for batch jobs only"},
        )
    return BatchLineRepository(session).get_lines(job_id)


@router.post("/jobs/{job_id}/lines/retry", response_model=BatchLinesResponse)
def retry_batch_lines(
    job_id: UUID,
    body: BatchLineRetryRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> BatchLinesResponse:
    """重试指定失败行 — 重置为 queued 状态并重新入队。"""
    record = get_job_for_user(session, job_id, user_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": "Job not found"},
        )
    if record.job_type.value != "batch":
        raise HTTPException(
            status_code=400,
            detail={"code": "NOT_BATCH_JOB", "message": "This endpoint is for batch jobs only"},
        )

    repo = BatchLineRepository(session)
    reset_count = repo.reset_lines_for_retry(job_id, body.line_indices)

    if reset_count > 0:
        # 重新入队让 BatchWorker 拾取
        queue = RedisJobQueue()
        queue.enqueue_batch(job_id)

    return repo.get_lines(job_id)

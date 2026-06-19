from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session
from domains.jobs.service import get_job_for_user, record_to_response
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from voice_platform.job.repository import BatchLineRepository
from voice_platform.job.schemas import BatchLineRetryRequest, BatchLinesResponse, JobResponse
from voice_platform.job.queue import RedisJobQueue

router = APIRouter()


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

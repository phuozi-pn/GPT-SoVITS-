from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_trace_id
from apps.api.quota_http import raise_quota_http
from domains.compliance.gateway import ComplianceError, ComplianceGateway
from domains.synthesis.service import SynthesisService
from fastapi import APIRouter, Depends, HTTPException
from voice_platform.config import get_db_session
from voice_platform.job.repository import VoiceVersionRepository
from voice_platform.job.schemas import SynthesisRequest, SynthesisResponse
from voice_platform.quota.exceptions import QuotaExceededError
from voice_platform.quota.repository import QuotaRepository
from sqlalchemy.orm import Session

router = APIRouter()
_gateway = ComplianceGateway()


def get_session():
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


@router.post("/synthesis", response_model=SynthesisResponse, status_code=202)
def create_synthesis(
    body: SynthesisRequest,
    user_id: UUID = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
    session: Session = Depends(get_session),
) -> SynthesisResponse:
    voices = VoiceVersionRepository(session)
    has_access = voices.user_can_access(body.voice_version_id, user_id)
    try:
        payload = _gateway.validate_synthesis(
            user_id=user_id,
            voice_version_id=body.voice_version_id,
            text=body.text,
            has_voice_access=has_access,
        )
    except ComplianceError as exc:
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "message": exc.message}) from exc

    quota = QuotaRepository(session)
    try:
        quota.ensure_chars_available(user_id, len(payload.text))
    except QuotaExceededError as exc:
        raise_quota_http(exc)

    payload.format = body.format
    service = SynthesisService(session)
    submitted = service.submit(owner_user_id=user_id, payload=payload, trace_id=trace_id)
    return SynthesisResponse(
        job_id=submitted.job_id,
        status=submitted.status,
        queue_position=submitted.queue_position,
    )

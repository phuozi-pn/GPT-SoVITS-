from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session, get_trace_id
from apps.api.exceptions import raise_domain_http
from domains.compliance.gateway import ComplianceError, ComplianceGateway
from domains.licensing.service import LicensingService, LicensingServiceError
from domains.quota.service import QuotaService, QuotaServiceError
from domains.synthesis.service import SynthesisService
from domains.voices.access import user_can_access_voice_version
from fastapi import APIRouter, Depends, HTTPException
from voice_platform.job.schemas import SynthesisRequest, SynthesisResponse
from sqlalchemy.orm import Session

router = APIRouter()
_gateway = ComplianceGateway()


@router.post("/synthesis", response_model=SynthesisResponse, status_code=202)
def create_synthesis(
    body: SynthesisRequest,
    user_id: UUID = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
    session: Session = Depends(get_session),
) -> SynthesisResponse:
    def can_access(voice_version_id: UUID) -> bool:
        return user_can_access_voice_version(session, voice_version_id, user_id)

    try:
        payload = _gateway.validate_synthesis_request(
            user_id=user_id,
            body=body,
            voice_access_checker=can_access,
        )
    except ComplianceError as exc:
        raise_domain_http(exc)

    licensing = LicensingService(session)
    try:
        if payload.segments:
            for seg in payload.segments:
                licensing.check_project_domain(
                    voice_version_id=seg.voice_version_id,
                    project_type=payload.project_type,
                )
                licensing.ensure_purchase_quota(
                    user_id=user_id,
                    voice_version_id=seg.voice_version_id,
                    char_count=len(seg.text),
                )
        elif payload.voice_version_id:
            licensing.check_project_domain(
                voice_version_id=payload.voice_version_id,
                project_type=payload.project_type,
            )
            licensing.ensure_purchase_quota(
                user_id=user_id,
                voice_version_id=payload.voice_version_id,
                char_count=payload.billed_char_count(),
            )
    except LicensingServiceError as exc:
        raise_domain_http(exc)

    try:
        QuotaService(session).ensure_chars_available(user_id, payload.billed_char_count())
    except QuotaServiceError as exc:
        raise_domain_http(exc)

    payload.format = body.format
    service = SynthesisService(session)
    submitted = service.submit(owner_user_id=user_id, payload=payload, trace_id=trace_id)
    return SynthesisResponse(
        job_id=submitted.job_id,
        status=submitted.status,
        queue_position=submitted.queue_position,
    )

from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session, get_trace_id
from apps.api.exceptions import raise_domain_http
from domains.compliance.gateway import ComplianceError, ComplianceGateway
from domains.developer.service import DeveloperService, DeveloperServiceError
from domains.licensing.service import LicensingService, LicensingServiceError
from domains.jobs.service import get_job_for_user, record_to_response
from domains.quota.service import QuotaService
from domains.synthesis.service import SynthesisService
from domains.voices.access import user_can_access_voice_version
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from voice_platform.developer.schemas import OpenSynthesisRequest, OpenSynthesisResponse
from voice_platform.job.schemas import JobResponse, SynthesisRequest

router = APIRouter()
_gateway = ComplianceGateway()


def get_open_api_user(
    x_api_key: str = Header(..., alias="X-Api-Key"),
    session: Session = Depends(get_session),
) -> tuple[UUID, object]:
    try:
        dev = DeveloperService(session)
        user_id, key_row = dev.resolve_user_from_key(x_api_key)
        return user_id, key_row
    except DeveloperServiceError as exc:
        raise_domain_http(exc)


@router.post("/open/synthesis", response_model=OpenSynthesisResponse, status_code=202)
def open_synthesis(
    body: OpenSynthesisRequest,
    auth: tuple[UUID, object] = Depends(get_open_api_user),
    trace_id: str = Depends(get_trace_id),
    session: Session = Depends(get_session),
) -> OpenSynthesisResponse:
    user_id, key_row = auth
    try:
        DeveloperService(session).require_scope(key_row, "synthesis:write")
    except DeveloperServiceError as exc:
        raise_domain_http(exc)

    def can_access(voice_version_id: UUID) -> bool:
        return user_can_access_voice_version(session, voice_version_id, user_id)

    synth_body = SynthesisRequest(
        voice_version_id=body.voice_version_id,
        text=body.text,
        format=body.format,
        ai_disclosure_ack=body.ai_disclosure_ack,
    )
    try:
        payload = _gateway.validate_synthesis_request(
            user_id=user_id,
            body=synth_body,
            voice_access_checker=can_access,
        )
    except ComplianceError as exc:
        raise_domain_http(exc)

    licensing = LicensingService(session)
    try:
        if payload.voice_version_id:
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
    payload.source_api_key_id = key_row.id
    submitted = SynthesisService(session).submit(
        owner_user_id=user_id,
        payload=payload,
        trace_id=trace_id,
    )
    return OpenSynthesisResponse(
        job_id=submitted.job_id,
        status=submitted.status.value,
        queue_position=submitted.queue_position,
    )


@router.get("/open/jobs/{job_id}", response_model=JobResponse)
def open_get_job(
    job_id: UUID,
    auth: tuple[UUID, object] = Depends(get_open_api_user),
    session: Session = Depends(get_session),
) -> JobResponse:
    user_id, key_row = auth
    try:
        DeveloperService(session).require_scope(key_row, "jobs:read")
    except DeveloperServiceError as exc:
        raise_domain_http(exc)

    record = get_job_for_user(session, job_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "Job not found"})
    return record_to_response(record)

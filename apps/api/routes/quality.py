from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session, require_admin_user
from apps.api.exceptions import raise_domain_http
from domains.quality.service import QualityService, QualityServiceError
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from voice_platform.job.schemas import AbTrialResponse, AbVoteRequest, AbVoteResponse, QualityReportResponse

router = APIRouter()


@router.get("/voice-versions/{voice_version_id}/quality", response_model=QualityReportResponse)
def get_quality_report(
    voice_version_id: UUID,
    _: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> QualityReportResponse:
    try:
        return QualityService(session).get_report(voice_version_id=voice_version_id)
    except QualityServiceError as exc:
        raise_domain_http(exc)


@router.post("/voice-versions/{voice_version_id}/quality/evaluate", response_model=QualityReportResponse)
def evaluate_quality(
    voice_version_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> QualityReportResponse:
    try:
        return QualityService(session).evaluate(voice_version_id=voice_version_id, owner_user_id=user_id)
    except QualityServiceError as exc:
        raise_domain_http(exc)


@router.post(
    "/admin/voice-versions/{voice_version_id}/quality/evaluate",
    response_model=QualityReportResponse,
)
def admin_evaluate_quality(
    voice_version_id: UUID,
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> QualityReportResponse:
    try:
        return QualityService(session).evaluate(voice_version_id=voice_version_id)
    except QualityServiceError as exc:
        raise_domain_http(exc)


@router.get("/voice-versions/{voice_version_id}/ab-trial", response_model=AbTrialResponse)
def get_ab_trial(
    voice_version_id: UUID,
    _: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> AbTrialResponse:
    try:
        return QualityService(session).create_ab_trial(voice_version_id=voice_version_id)
    except QualityServiceError as exc:
        raise_domain_http(exc)


@router.post("/voice-versions/{voice_version_id}/ab-vote", response_model=AbVoteResponse)
def submit_ab_vote(
    voice_version_id: UUID,
    body: AbVoteRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> AbVoteResponse:
    try:
        return QualityService(session).submit_ab_vote(
            voice_version_id=voice_version_id,
            voter_user_id=user_id,
            body=body,
            slot_a_kind=body.slot_a_kind,
            slot_b_kind=body.slot_b_kind,
        )
    except QualityServiceError as exc:
        raise_domain_http(exc)

"""REQ-015 marketplace invite and waitlist routes."""

from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session, require_admin_user
from apps.api.exceptions import raise_domain_http
from domains.marketplace.invite_service import MarketplaceInviteService, MarketplaceInviteServiceError
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from voice_platform.marketplace.schemas import (
    InviteCodeCreateRequest,
    InviteCodeSummary,
    InviteRedeemRequest,
    InviteRedeemResponse,
    PublishEligibilityResponse,
    WaitlistEntrySummary,
    WaitlistIssueRequest,
    WaitlistIssueResponse,
    WaitlistJoinRequest,
    WaitlistJoinResponse,
)

router = APIRouter()


@router.get("/marketplace/publish-eligibility", response_model=PublishEligibilityResponse)
def publish_eligibility(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> PublishEligibilityResponse:
    return MarketplaceInviteService(session).get_publish_eligibility(user_id=user_id)


@router.post("/marketplace/waitlist", response_model=WaitlistJoinResponse, status_code=201)
def join_waitlist(
    body: WaitlistJoinRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> WaitlistJoinResponse:
    return MarketplaceInviteService(session).join_waitlist(
        user_id=user_id,
        contact=body.contact,
        note=body.note,
    )


@router.post("/marketplace/invite/redeem", response_model=InviteRedeemResponse)
def redeem_invite(
    body: InviteRedeemRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> InviteRedeemResponse:
    try:
        return MarketplaceInviteService(session).redeem_invite(user_id=user_id, code=body.code)
    except MarketplaceInviteServiceError as exc:
        raise_domain_http(exc)


@router.post("/admin/marketplace/invite-codes", response_model=InviteCodeSummary, status_code=201)
def create_invite_code(
    body: InviteCodeCreateRequest,
    admin_id: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> InviteCodeSummary:
    try:
        return MarketplaceInviteService(session).create_invite_code(admin_user_id=admin_id, body=body)
    except MarketplaceInviteServiceError as exc:
        raise_domain_http(exc)


@router.get("/admin/marketplace/invite-codes", response_model=list[InviteCodeSummary])
def list_invite_codes(
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> list[InviteCodeSummary]:
    return MarketplaceInviteService(session).list_invite_codes()


@router.get("/admin/marketplace/waitlist", response_model=list[WaitlistEntrySummary])
def list_waitlist(
    limit: int = 50,
    _: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> list[WaitlistEntrySummary]:
    return MarketplaceInviteService(session).list_waitlist(limit=min(limit, 200))


@router.post(
    "/admin/marketplace/waitlist/{waitlist_id}/issue-invite",
    response_model=WaitlistIssueResponse,
)
def issue_waitlist_invite(
    waitlist_id: UUID,
    body: WaitlistIssueRequest | None = None,
    admin_id: UUID = Depends(require_admin_user),
    session: Session = Depends(get_session),
) -> WaitlistIssueResponse:
    try:
        return MarketplaceInviteService(session).issue_invite_from_waitlist(
            waitlist_id=waitlist_id,
            admin_user_id=admin_id,
            body=body,
        )
    except MarketplaceInviteServiceError as exc:
        raise_domain_http(exc)

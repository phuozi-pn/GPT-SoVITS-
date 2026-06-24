"""REQ-015 invite-only catalog publish and waitlist."""

from __future__ import annotations

from uuid import UUID

from voice_platform.config import get_settings
from voice_platform.auth.repository import UserRepository
from voice_platform.marketplace.repository import MarketplaceInviteRepository
from voice_platform.marketplace.schemas import (
    InviteCodeCreateRequest,
    InviteCodeSummary,
    InviteRedeemResponse,
    PublishEligibilityResponse,
    WaitlistEntrySummary,
    WaitlistIssueRequest,
    WaitlistIssueResponse,
    WaitlistJoinResponse,
)
from voice_platform.job.repository import QualityReportRepository


class MarketplaceInviteServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class MarketplaceInviteService:
    def __init__(self, session) -> None:
        self._session = session
        self._invites = MarketplaceInviteRepository(session)
        self._quality = QualityReportRepository(session)

    def get_publish_eligibility(self, *, user_id: UUID) -> PublishEligibilityResponse:
        settings = get_settings()
        invited = self._invites.has_active_invite(user_id)
        on_waitlist = self._invites.get_waitlist(user_id) is not None
        invite_required = settings.marketplace_invite_required

        if not invite_required or invited:
            can_publish = True
            reason = None
            message = None
        else:
            can_publish = False
            reason = "INVITE_REQUIRED"
            message = "需要有效邀请码才能提交上架申请，可先加入候补名单。"

        return PublishEligibilityResponse(
            can_publish=can_publish,
            invite_required=invite_required,
            invited=invited,
            on_waitlist=on_waitlist,
            quality_gate=settings.marketplace_quality_gate,
            reason=reason,
            message=message,
        )

    def ensure_can_publish(self, *, user_id: UUID) -> None:
        settings = get_settings()
        if not settings.marketplace_invite_required:
            return
        if self._invites.has_active_invite(user_id):
            return
        raise MarketplaceInviteServiceError(
            "INVITE_REQUIRED",
            "Valid marketplace invite required before catalog publish",
            403,
        )

    def ensure_quality_pass(self, *, voice_version_id: UUID) -> None:
        settings = get_settings()
        if not settings.marketplace_quality_gate:
            return
        report = self._quality.get(voice_version_id)
        if not report or not report.quality_pass:
            raise MarketplaceInviteServiceError(
                "QUALITY_REQUIRED",
                "Voice version must pass similarity evaluation before catalog publish",
                403,
            )

    def join_waitlist(
        self,
        *,
        user_id: UUID,
        contact: str,
        note: str,
    ) -> WaitlistJoinResponse:
        self._invites.join_waitlist(user_id=user_id, contact=contact.strip(), note=note.strip())
        return WaitlistJoinResponse(
            on_waitlist=True,
            message="已加入上架候补名单，运营审核通过后将发放邀请码。",
        )

    def redeem_invite(self, *, user_id: UUID, code: str) -> InviteRedeemResponse:
        try:
            self._invites.redeem_code(user_id=user_id, code=code)
        except ValueError as exc:
            err = str(exc)
            messages = {
                "INVALID_CODE": "邀请码无效",
                "CODE_REVOKED": "邀请码已撤销",
                "CODE_EXPIRED": "邀请码已过期",
                "CODE_EXHAUSTED": "邀请码已达使用上限",
            }
            raise MarketplaceInviteServiceError(
                err,
                messages.get(err, "邀请码不可用"),
                400,
            ) from exc
        normalized = code.strip().upper()
        return InviteRedeemResponse(
            invited=True,
            code=normalized,
            message="邀请码兑换成功，现在可以提交音色馆上架申请。",
        )

    def create_invite_code(
        self,
        *,
        admin_user_id: UUID,
        body: InviteCodeCreateRequest,
    ) -> InviteCodeSummary:
        try:
            row = self._invites.create_code(
                code=body.code,
                max_uses=body.max_uses,
                note=body.note,
                created_by=admin_user_id,
                expires_in_days=body.expires_in_days,
            )
        except ValueError as exc:
            if str(exc) == "CODE_EXISTS":
                raise MarketplaceInviteServiceError("CODE_EXISTS", "Invite code already exists", 409) from exc
            raise
        return self._code_summary(row)

    def list_invite_codes(self) -> list[InviteCodeSummary]:
        return [self._code_summary(row) for row in self._invites.list_codes()]

    def list_waitlist(self, *, limit: int = 50) -> list[WaitlistEntrySummary]:
        users = UserRepository(self._session)
        rows = self._invites.list_waitlist_pending(limit=limit)
        summaries: list[WaitlistEntrySummary] = []
        for row in rows:
            user = users.get_by_id(row.user_id)
            summaries.append(
                WaitlistEntrySummary(
                    waitlist_id=row.id,
                    user_id=row.user_id,
                    phone=user.phone if user else "",
                    contact=row.contact,
                    note=row.note,
                    created_at=row.created_at,
                )
            )
        return summaries

    def issue_invite_from_waitlist(
        self,
        *,
        waitlist_id: UUID,
        admin_user_id: UUID,
        body: WaitlistIssueRequest | None = None,
    ) -> WaitlistIssueResponse:
        row = self._invites.get_waitlist_by_id(waitlist_id)
        if not row:
            raise MarketplaceInviteServiceError("WAITLIST_NOT_FOUND", "Waitlist entry not found", 404)
        if row.fulfilled_at is not None:
            raise MarketplaceInviteServiceError("WAITLIST_FULFILLED", "Waitlist entry already fulfilled", 409)

        if self._invites.has_active_invite(row.user_id):
            redemption = self._invites.get_redemption(row.user_id)
            invite_code_id = redemption.invite_code_id if redemption else row.id
            self._invites.mark_waitlist_fulfilled(row, invite_code_id=invite_code_id)
            return WaitlistIssueResponse(
                waitlist_id=row.id,
                user_id=row.user_id,
                code="",
                message="用户已有邀请资格，已标记候补完成。",
            )

        req = body or WaitlistIssueRequest()
        code = (req.code or f"PHONIA-{row.user_id.hex[:8].upper()}").strip().upper()
        try:
            invite = self._invites.create_code(
                code=code,
                max_uses=1,
                note=f"waitlist issue for {row.user_id}",
                created_by=admin_user_id,
                expires_in_days=req.expires_in_days,
            )
            self._invites.redeem_code(user_id=row.user_id, code=invite.code)
            self._invites.mark_waitlist_fulfilled(row, invite_code_id=invite.id)
        except ValueError as exc:
            if str(exc) == "CODE_EXISTS":
                raise MarketplaceInviteServiceError("CODE_EXISTS", "Invite code already exists", 409) from exc
            raise
        return WaitlistIssueResponse(
            waitlist_id=row.id,
            user_id=row.user_id,
            code=invite.code,
            message=f"已向用户发放邀请码 {invite.code}",
        )

    @staticmethod
    def _code_summary(row) -> InviteCodeSummary:
        return InviteCodeSummary(
            invite_code_id=row.id,
            code=row.code,
            max_uses=row.max_uses,
            used_count=row.used_count,
            note=row.note or "",
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
            created_at=row.created_at,
        )

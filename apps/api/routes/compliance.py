"""Compliance pre-check API — text validation before synthesis."""

from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id
from domains.compliance.gateway import ComplianceGateway
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

router = APIRouter()


class TextComplianceIssue(BaseModel):
    code: str
    message: str
    segment_index: int | None = None


class TextCompliancePrecheckRequest(BaseModel):
    texts: list[str] = Field(default_factory=list, max_length=50)
    segmented: bool = False


class TextCompliancePrecheckResponse(BaseModel):
    ok: bool
    total_chars: int
    issues: list[TextComplianceIssue]


@router.post("/compliance/precheck", response_model=TextCompliancePrecheckResponse)
def precheck_synthesis_text(
    body: TextCompliancePrecheckRequest,
    _: UUID = Depends(get_current_user_id),
) -> TextCompliancePrecheckResponse:
    """Scan script text for length / sensitive-word issues before submitting synthesis."""
    gateway = ComplianceGateway()
    issues = [
        TextComplianceIssue(**item)
        for item in gateway.precheck_texts(body.texts, segmented=body.segmented)
    ]
    total_chars = sum(len((t or "").strip()) for t in body.texts)
    return TextCompliancePrecheckResponse(ok=not issues, total_chars=total_chars, issues=issues)

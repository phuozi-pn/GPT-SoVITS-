from __future__ import annotations

from apps.api.deps import get_current_user_id, get_session
from domains.quota.service import QuotaService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from voice_platform.quota.schemas import QuotaSummary

router = APIRouter()


@router.get("/usage/quota", response_model=QuotaSummary)
def get_quota(
    user_id=Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> QuotaSummary:
    return QuotaService(session).get_summary(user_id)

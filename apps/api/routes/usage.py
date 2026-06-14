from __future__ import annotations

from apps.api.deps import get_current_user_id
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from voice_platform.config import get_db_session
from voice_platform.quota.repository import QuotaRepository
from voice_platform.quota.schemas import QuotaSummary

router = APIRouter()


def get_session():
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


@router.get("/usage/quota", response_model=QuotaSummary)
def get_quota(
    user_id=Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> QuotaSummary:
    return QuotaRepository(session).get_summary(user_id)

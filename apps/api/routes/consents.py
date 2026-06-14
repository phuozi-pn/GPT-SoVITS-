from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id
from domains.consents.service import ConsentService, ConsentServiceError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from voice_platform.config import get_db_session
from voice_platform.job.schemas import ConsentCreateRequest, ConsentCreateResponse

router = APIRouter()


def get_session():
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


@router.post("/consents", response_model=ConsentCreateResponse, status_code=201)
def create_consent(
    body: ConsentCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> ConsentCreateResponse:
    service = ConsentService(session)
    try:
        return service.create(owner_user_id=user_id, voice_id=body.voice_id)
    except ConsentServiceError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

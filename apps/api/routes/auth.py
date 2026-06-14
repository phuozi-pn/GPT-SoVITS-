from __future__ import annotations

from apps.api.deps import get_trace_id
from domains.auth.service import AuthError, AuthService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from voice_platform.auth.schemas import LoginRequest, LoginResponse, SmsSendRequest, SmsSendResponse
from voice_platform.config import get_db_session

router = APIRouter()


def get_session():
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


@router.post("/auth/sms/send", response_model=SmsSendResponse)
def send_sms(
    body: SmsSendRequest,
    session: Session = Depends(get_session),
    _: str = Depends(get_trace_id),
) -> SmsSendResponse:
    service = AuthService(session)
    try:
        return service.send_sms(body.phone)
    except AuthError as exc:
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/auth/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    session: Session = Depends(get_session),
    _: str = Depends(get_trace_id),
) -> LoginResponse:
    service = AuthService(session)
    try:
        return service.login(body.phone, body.code)
    except AuthError as exc:
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "message": exc.message}) from exc

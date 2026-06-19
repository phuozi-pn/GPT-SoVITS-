from __future__ import annotations

from apps.api.deps import get_session, get_trace_id
from apps.api.exceptions import raise_domain_http
from domains.auth.service import AuthError, AuthService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from voice_platform.auth.schemas import LoginRequest, LoginResponse, SmsSendRequest, SmsSendResponse

router = APIRouter()


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
        raise_domain_http(exc)


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
        raise_domain_http(exc)

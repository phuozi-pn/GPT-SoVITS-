from __future__ import annotations

import logging

from voice_platform.auth.jwt import create_access_token
from voice_platform.auth.otp import OtpStore
from voice_platform.auth.repository import UserRepository
from voice_platform.auth.schemas import LoginResponse, SmsSendResponse, UserInfo
from voice_platform.config import get_settings
from voice_platform.quota.repository import QuotaRepository

logger = logging.getLogger(__name__)


class AuthError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class AuthService:
    def __init__(self, session, otp_store: OtpStore | None = None) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._otp = otp_store or OtpStore()
        self._settings = get_settings()

    def send_sms(self, phone: str) -> SmsSendResponse:
        if self._otp.is_locked(phone):
            raise AuthError("ACCOUNT_LOCKED", "Account locked due to too many failed attempts", 429)

        code = self._otp.issue(phone)
        mock_code = None
        if self._settings.sms_mock:
            mock_code = code
            logger.info("SMS mock: phone=%s code=%s", phone, code)
        else:
            # W1: real SMS gateway not wired; fail closed unless mock enabled
            raise AuthError("SMS_UNAVAILABLE", "SMS gateway not configured", 503)

        return SmsSendResponse(mock_code=mock_code)

    def login(self, phone: str, code: str) -> LoginResponse:
        if self._otp.is_locked(phone):
            raise AuthError("ACCOUNT_LOCKED", "Account locked due to too many failed attempts", 429)

        dev_code = self._settings.dev_otp_code
        if dev_code and code == dev_code:
            ok = True
        elif self._settings.sms_mock:
            ok = self._otp.verify(phone, code)
        else:
            raise AuthError("SMS_UNAVAILABLE", "SMS gateway not configured", 503)

        if not ok:
            raise AuthError("INVALID_OTP", "Invalid or expired verification code", 401)

        user = self._users.get_or_create(phone)
        if user.status != "active":
            raise AuthError("AUTH_REQUIRED", "Account disabled", 403)

        token = create_access_token(user_id=user.id)
        quota = QuotaRepository(self._session).get_summary(user.id)
        return LoginResponse(
            access_token=token,
            expires_in_days=self._settings.jwt_expire_days,
            user=UserInfo(user_id=user.id, phone=user.phone),
            quota=quota,
        )

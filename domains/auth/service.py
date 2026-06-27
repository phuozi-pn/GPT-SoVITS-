from __future__ import annotations

import logging
from uuid import UUID

from voice_platform.auth.identifiers import email_otp_key, normalize_email
from voice_platform.auth.jwt import TokenError, create_access_token, decode_access_token
from voice_platform.auth.otp import OtpStore
from voice_platform.auth.repository import UserRepository
from voice_platform.auth.schemas import LoginResponse, SmsSendResponse, UserInfo
from voice_platform.config import get_settings
from voice_platform.email.resend import ResendClient, ResendError
from voice_platform.quota.repository import QuotaRepository
from voice_platform.social.system import ensure_system_user

logger = logging.getLogger(__name__)

SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
VIEWER_ANONYMOUS = UUID("00000000-0000-0000-0000-000000000000")


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

    # ---- JWT / token ----

    @staticmethod
    def decode_token(token: str) -> UUID:
        """Decode a JWT access token and return the user ID.

        Raises AuthError on invalid/expired tokens.
        """
        try:
            return decode_access_token(token)
        except TokenError as exc:
            raise AuthError("AUTH_REQUIRED", str(exc), 401) from exc

    # ---- User management helpers ----

    def ensure_dev_user(self, user_id: UUID) -> None:
        """Create or verify a dev-mode user."""
        self._users.ensure_dev_user(user_id)

    def ensure_system_user(self) -> None:
        """Ensure the system user exists for system notices."""
        ensure_system_user(self._session)

    # ---- OTP helpers ----

    def _send_sms_otp(self, *, phone: str) -> SmsSendResponse:
        if self._otp.is_locked(phone):
            raise AuthError("ACCOUNT_LOCKED", "Account locked due to too many failed attempts", 429)

        code = self._otp.issue(phone)
        if self._settings.sms_mock:
            logger.info("SMS mock: phone=%s code=%s", phone, code)
            return SmsSendResponse(mock_code=code)
        raise AuthError("SMS_UNAVAILABLE", "SMS gateway not configured", 503)

    def _send_email_otp(self, *, email: str) -> SmsSendResponse:
        otp_key = email_otp_key(email)
        if self._otp.is_locked(otp_key):
            raise AuthError("ACCOUNT_LOCKED", "Account locked due to too many failed attempts", 429)

        code = self._otp.issue(otp_key)
        ttl_minutes = max(1, self._settings.sms_otp_ttl_sec // 60)

        if self._settings.resend_configured:
            client = ResendClient()
            try:
                client.send_login_code(to_email=email, code=code, ttl_minutes=ttl_minutes)
            except ResendError as exc:
                raise AuthError(exc.code, exc.message, 502) from exc
            logger.info("Email sent via Resend: %s", email)
            return SmsSendResponse(message="验证码已发送至邮箱")

        if self._settings.sms_mock:
            logger.info("Email mock: %s code=%s", email, code)
            return SmsSendResponse(mock_code=code)

        raise AuthError(
            "EMAIL_UNAVAILABLE",
            "邮件服务未配置，请设置 RESEND_API_KEY 与 RESEND_FROM_EMAIL",
            503,
        )

    def _login_with_otp(
        self,
        *,
        otp_key: str,
        code: str,
        channel: str,
        resolve_user,
    ) -> LoginResponse:
        if self._otp.is_locked(otp_key):
            raise AuthError("ACCOUNT_LOCKED", "Account locked due to too many failed attempts", 429)

        dev_code = self._settings.dev_otp_code
        if dev_code and code == dev_code:
            ok = True
        elif channel == "email" and (
            self._settings.resend_configured or self._settings.sms_mock
        ):
            ok = self._otp.verify(otp_key, code)
        elif channel == "sms" and self._settings.sms_mock:
            ok = self._otp.verify(otp_key, code)
        else:
            label = "EMAIL" if channel == "email" else "SMS"
            raise AuthError(f"{label}_UNAVAILABLE", f"{label} gateway not configured", 503)

        if not ok:
            raise AuthError("INVALID_OTP", "Invalid or expired verification code", 401)

        user = resolve_user()
        if user.status != "active":
            raise AuthError("AUTH_REQUIRED", "Account disabled", 403)

        token = create_access_token(user_id=user.id)
        quota = QuotaRepository(self._session).get_summary(user.id)
        return LoginResponse(
            access_token=token,
            expires_in_days=self._settings.jwt_expire_days,
            user=UserInfo(
                user_id=user.id,
                phone=user.phone,
                email=user.email,
                verified=user.verified,
            ),
            quota=quota,
        )

    # ---- SMS / login ----

    def send_sms(self, phone: str) -> SmsSendResponse:
        return self._send_sms_otp(phone=phone)

    def login(self, phone: str, code: str) -> LoginResponse:
        return self._login_with_otp(
            otp_key=phone,
            code=code,
            channel="sms",
            resolve_user=lambda: self._users.get_or_create(phone),
        )

    # ---- Email / login ----

    def send_email(self, email: str) -> SmsSendResponse:
        normalized = normalize_email(email)
        return self._send_email_otp(email=normalized)

    def login_with_email(self, email: str, code: str) -> LoginResponse:
        normalized = normalize_email(email)
        return self._login_with_otp(
            otp_key=email_otp_key(normalized),
            code=code,
            channel="email",
            resolve_user=lambda: self._users.get_or_create_by_email(normalized),
        )

from __future__ import annotations

import secrets

import redis

from voice_platform.config import get_settings


class OtpStore:
    def __init__(self, client: redis.Redis | None = None) -> None:
        settings = get_settings()
        self._client = client or redis.Redis.from_url(settings.redis_url, decode_responses=True)
        self._ttl = settings.sms_otp_ttl_sec
        self._max_failures = settings.auth_otp_max_failures
        self._lock_ttl = settings.auth_lock_ttl_sec

    def _otp_key(self, phone: str) -> str:
        return f"otp:{phone}"

    def _fail_key(self, phone: str) -> str:
        return f"otp:fail:{phone}"

    def _lock_key(self, phone: str) -> str:
        return f"otp:lock:{phone}"

    def is_locked(self, phone: str) -> bool:
        return bool(self._client.exists(self._lock_key(phone)))

    def issue(self, phone: str) -> str:
        code = f"{secrets.randbelow(1_000_000):06d}"
        self._client.setex(self._otp_key(phone), self._ttl, code)
        self._client.delete(self._fail_key(phone))
        return code

    def verify(self, phone: str, code: str) -> bool:
        if self.is_locked(phone):
            return False
        stored = self._client.get(self._otp_key(phone))
        if not stored or stored != code:
            fails = int(self._client.incr(self._fail_key(phone)))
            if fails == 1:
                self._client.expire(self._fail_key(phone), self._lock_ttl)
            if fails >= self._max_failures:
                self._client.setex(self._lock_key(phone), self._lock_ttl, "1")
            return False
        self._client.delete(self._otp_key(phone))
        self._client.delete(self._fail_key(phone))
        return True

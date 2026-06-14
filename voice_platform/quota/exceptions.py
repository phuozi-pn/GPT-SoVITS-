from __future__ import annotations

from datetime import datetime


class QuotaExceededError(Exception):
    def __init__(
        self,
        *,
        quota_type: str,
        message: str,
        required: int,
        remaining: int,
        monthly_limit: int,
        used: int,
        reset_at: datetime,
    ) -> None:
        self.quota_type = quota_type
        self.message = message
        self.required = required
        self.remaining = remaining
        self.monthly_limit = monthly_limit
        self.used = used
        self.reset_at = reset_at
        super().__init__(message)

    def to_detail(self) -> dict:
        return {
            "code": "QUOTA_EXCEEDED",
            "message": self.message,
            "details": {
                "quota_type": self.quota_type,
                "required": self.required,
                "remaining": self.remaining,
                "monthly_limit": self.monthly_limit,
                "used": self.used,
                "reset_at": self.reset_at.isoformat(),
                "upgrade_url": "/billing",
            },
        }

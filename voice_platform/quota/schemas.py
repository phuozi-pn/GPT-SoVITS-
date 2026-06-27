from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class QuotaSummary(BaseModel):
    monthly_char_limit: int
    chars_used: int
    chars_remaining: int
    wallet_token_balance: int = 0
    total_tokens_remaining: int = 0
    monthly_train_limit: int
    trainings_used: int
    trainings_remaining: int
    reset_at: datetime


class UserUsageReportRow(BaseModel):
    user_id: str
    phone: str
    chars_used: int
    trainings_used: int
    monthly_char_limit: int
    monthly_train_limit: int
    chars_remaining: int
    trainings_remaining: int

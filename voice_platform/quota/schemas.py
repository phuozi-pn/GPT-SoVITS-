from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class QuotaSummary(BaseModel):
    monthly_char_limit: int
    chars_used: int
    chars_remaining: int
    monthly_train_limit: int
    trainings_used: int
    trainings_remaining: int
    reset_at: datetime

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from voice_platform.config import get_settings


def quota_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().quota_timezone)


def current_billing_month() -> str:
    return datetime.now(quota_timezone()).strftime("%Y-%m")


def next_reset_at() -> datetime:
    tz = quota_timezone()
    now = datetime.now(tz)
    if now.month == 12:
        return datetime(now.year + 1, 1, 1, tzinfo=tz)
    return datetime(now.year, now.month + 1, 1, tzinfo=tz)

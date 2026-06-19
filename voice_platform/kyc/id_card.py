"""Chinese ID card helpers (format + age gate for REQ-002)."""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime

_ID_RE = re.compile(
    r"^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dX]$"
)


def hash_id_number(id_number: str) -> str:
    return hashlib.sha256(id_number.encode("utf-8")).hexdigest()


def mask_real_name(name: str) -> str:
    if len(name) <= 1:
        return "*"
    return name[0] + "*" * (len(name) - 1)


def parse_birth_date(id_number: str) -> date | None:
    if not _ID_RE.match(id_number):
        return None
    try:
        return datetime.strptime(id_number[6:14], "%Y%m%d").date()
    except ValueError:
        return None


def is_valid_id_format(id_number: str) -> bool:
    return _ID_RE.match(id_number) is not None


def is_adult(id_number: str, *, today: date | None = None) -> bool:
    birth = parse_birth_date(id_number)
    if birth is None:
        return False
    ref = today or date.today()
    age = ref.year - birth.year - ((ref.month, ref.day) < (birth.month, birth.day))
    return age >= 18

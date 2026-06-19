"""Unit tests for Chinese ID validation helpers."""

from __future__ import annotations

from datetime import date

from voice_platform.kyc.id_card import is_adult, is_valid_id_format, mask_real_name, parse_birth_date


def test_valid_adult_id():
    assert is_valid_id_format("110101199001011234")
    assert parse_birth_date("110101199001011234") == date(1990, 1, 1)
    assert is_adult("110101199001011234", today=date(2026, 6, 10))


def test_minor_rejected():
    assert is_valid_id_format("110101201501011234")
    assert not is_adult("110101201501011234", today=date(2026, 6, 10))


def test_mask_name():
    assert mask_real_name("张三") == "张*"

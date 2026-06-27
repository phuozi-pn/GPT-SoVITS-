"""Email identifier validation tests."""

from voice_platform.auth.identifiers import email_otp_key, mask_email, validate_email


def test_validate_email_ok():
    assert validate_email(" User@Example.COM ") == "user@example.com"


def test_email_otp_key_normalized():
    assert email_otp_key("User@Example.com") == "email:user@example.com"


def test_mask_email():
    assert mask_email("alice@example.com") == "a***e@example.com"

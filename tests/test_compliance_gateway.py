from __future__ import annotations

from uuid import UUID

import pytest

from domains.compliance.gateway import ComplianceError, ComplianceGateway

GATEWAY = ComplianceGateway()
USER = UUID("00000000-0000-0000-0000-000000000001")
VOICE = UUID("11111111-1111-1111-1111-111111111101")


def test_synthesis_ok():
    payload = GATEWAY.validate_synthesis(
        user_id=USER,
        voice_version_id=VOICE,
        text="你好，测试。",
        has_voice_access=True,
    )
    assert payload.text == "你好，测试。"
    assert payload.voice_version_id == VOICE


def test_voice_not_granted():
    with pytest.raises(ComplianceError) as exc:
        GATEWAY.validate_synthesis(
            user_id=USER,
            voice_version_id=VOICE,
            text="你好",
            has_voice_access=False,
        )
    assert exc.value.code == "VOICE_NOT_GRANTED"
    assert exc.value.http_status == 403


def test_invalid_text_empty():
    with pytest.raises(ComplianceError) as exc:
        GATEWAY.validate_synthesis(
            user_id=USER,
            voice_version_id=VOICE,
            text="   ",
            has_voice_access=True,
        )
    assert exc.value.code == "INVALID_TEXT"


def test_sensitive_word():
    with pytest.raises(ComplianceError) as exc:
        GATEWAY.validate_synthesis(
            user_id=USER,
            voice_version_id=VOICE,
            text="这里有测试敏感词",
            has_voice_access=True,
        )
    assert exc.value.code == "SENSITIVE_WORD"


def test_ai_disclosure_required():
    with pytest.raises(ComplianceError) as exc:
        GATEWAY.validate_synthesis(
            user_id=USER,
            voice_version_id=VOICE,
            text="你好",
            has_voice_access=True,
            ai_disclosure_ack=False,
        )
    assert exc.value.code == "AI_DISCLOSURE_REQUIRED"


VOICE_PROFILE = UUID("11111111-1111-1111-1111-111111111100")


def test_train_ok():
    GATEWAY.validate_train(
        user_id=USER,
        voice_id=VOICE_PROFILE,
        owns_voice=True,
        consent_approved=True,
        asset_locked=True,
        asset_qc_passed=True,
        model_tag="gsv-v2pro-20250606",
    )


def test_train_forbidden():
    with pytest.raises(ComplianceError) as exc:
        GATEWAY.validate_train(
            user_id=USER,
            voice_id=VOICE_PROFILE,
            owns_voice=False,
            consent_approved=True,
            asset_locked=True,
            asset_qc_passed=True,
            model_tag="gsv-v2pro-20250606",
        )
    assert exc.value.code == "FORBIDDEN"


def test_train_consent_required():
    with pytest.raises(ComplianceError) as exc:
        GATEWAY.validate_train(
            user_id=USER,
            voice_id=VOICE_PROFILE,
            owns_voice=True,
            consent_approved=False,
            asset_locked=True,
            asset_qc_passed=True,
            model_tag="gsv-v2pro-20250606",
        )
    assert exc.value.code == "CONSENT_REQUIRED"

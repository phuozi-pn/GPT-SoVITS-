from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from domains.training.service import TrainingService


def test_resolve_train_inputs_cloud_options_in_hyperparams():
    voice_id = uuid4()
    asset_id = uuid4()
    consent_id = uuid4()
    asset = MagicMock()
    asset.id = asset_id
    asset.locked = True
    asset.qc_passed = True
    asset.storage_uri = "local://voices/x.wav"
    asset.qc_result_json = {"ref_text": "测试参考文本。"}
    consent = MagicMock()
    consent.id = consent_id
    consent.status = "approved"

    session = MagicMock()
    voices = MagicMock()
    voices.user_owns_voice.return_value = True
    voices.get_asset.return_value = asset
    voices.get_consent.return_value = consent

    svc = TrainingService(session)
    svc._voices = voices

    payload, owns, consent_ok, locked, qc = svc.resolve_train_inputs(
        voice_id=voice_id,
        owner_user_id=uuid4(),
        voice_asset_id=asset_id,
        consent_id=consent_id,
        model_tag="gsv-v2pro-20250606",
        train_backend="cloud",
        cloud_local_dataset_prep=False,
        cloud_use_asr=True,
    )

    assert payload is not None
    assert payload.hyperparams["train_backend"] == "cloud"
    assert payload.hyperparams["cloud_local_dataset_prep"] is False
    assert payload.hyperparams["cloud_use_asr"] is True
    assert owns and consent_ok and locked and qc

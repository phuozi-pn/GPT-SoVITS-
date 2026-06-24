from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session
from domains.cloud_train.service import user_can_cloud_train
from domains.training.validate import cloud_train_issues
from domains.voices.import_service import engine_train_root_ready
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from voice_platform.cloud_train.config import is_cloud_train_configured
from voice_platform.config import get_settings
from voice_platform.engine.spike_config import load_spike_train_config, spike_epoch_label
from workers.train.mode import resolve_train_mode, train_mode_description

router = APIRouter()


class PlatformCapabilitiesResponse(BaseModel):
    train_mode: str
    train_mode_label: str
    engine_mock: bool
    engine_tts_url: str
    train_mock: bool
    kyc_required: bool
    kyc_mock: bool
    asr_enabled: bool
    asr_available: bool
    cloud_train_configured: bool
    cloud_train_available: bool
    cloud_train_issues: list[str]
    engine_train_root_ready: bool
    weight_import_available: bool
    quick_clone_available: bool
    cloud_train_self_service: bool
    cloud_train_user_connected: bool
    cloud_train_local_dataset_prep_default: bool
    cloud_train_use_asr_default: bool
    cloud_train_gpt_epochs: int
    cloud_train_sovits_epochs: int
    cloud_train_epoch_label: str


@router.get("/platform/capabilities", response_model=PlatformCapabilitiesResponse)
def platform_capabilities(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> PlatformCapabilitiesResponse:
    settings = get_settings()
    spike = load_spike_train_config()
    mode = resolve_train_mode()
    from voice_platform.asr.service import AssetAsrService

    asr = AssetAsrService(settings)
    cloud_ok = is_cloud_train_configured(settings)
    engine_ready, _ = engine_train_root_ready()
    issues = cloud_train_issues()
    self_service = engine_ready and not settings.train_mock
    user_connected = user_can_cloud_train(session, user_id)
    return PlatformCapabilitiesResponse(
        train_mode=mode,
        train_mode_label=train_mode_description(mode),
        engine_mock=settings.engine_mock,
        engine_tts_url=settings.engine_tts_url,
        train_mock=settings.train_mock,
        kyc_required=settings.kyc_required,
        kyc_mock=settings.kyc_mock,
        asr_enabled=settings.asset_asr_enabled,
        asr_available=asr.is_available(),
        cloud_train_configured=cloud_ok,
        cloud_train_available=self_service,
        cloud_train_issues=issues,
        engine_train_root_ready=engine_ready,
        weight_import_available=engine_ready and not settings.train_mock,
        quick_clone_available=not settings.train_mock,
        cloud_train_self_service=self_service,
        cloud_train_user_connected=user_connected,
        cloud_train_local_dataset_prep_default=settings.cloud_train_local_dataset_prep,
        cloud_train_use_asr_default=settings.train_use_asr and asr.is_available(),
        cloud_train_gpt_epochs=int(spike.get("gpt_epochs", 12)),
        cloud_train_sovits_epochs=int(spike.get("sovits_epochs", 12)),
        cloud_train_epoch_label=spike_epoch_label(spike),
    )

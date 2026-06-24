from __future__ import annotations

from voice_platform.engine.spike_config import estimate_cloud_train_minutes, load_spike_train_config, spike_epoch_label


def test_load_spike_train_config_epochs():
    cfg = load_spike_train_config()
    assert int(cfg["gpt_epochs"]) >= 12
    assert int(cfg["sovits_epochs"]) >= 12
    assert cfg.get("is_half") is False
    assert spike_epoch_label(cfg) == f"{cfg['gpt_epochs']}+{cfg['sovits_epochs']}"


def test_estimate_cloud_train_minutes_scales_with_segments():
    low, high = estimate_cloud_train_minutes(segment_count=37, cfg={"gpt_epochs": 8, "sovits_epochs": 8})
    assert low >= 15
    assert high > low

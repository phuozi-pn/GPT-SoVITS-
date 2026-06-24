"""Engine weight resolution — prevent api_v2 cross-voice contamination."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from voice_platform.engine.infer_weights import read_v2pro_base_weights, resolve_synthesis_weights


def test_read_v2pro_base_weights_from_yaml(tmp_path):
    engine = tmp_path / "engine"
    cfg = engine / "GPT_SoVITS/configs"
    cfg.mkdir(parents=True)
    (cfg / "tts_infer_v2pro.yaml").write_text(
        """
custom:
  t2s_weights_path: GPT_weights_v2Pro/old-finetune.ckpt
  vits_weights_path: SoVITS_weights_v2Pro/old-finetune.pth
v2Pro:
  t2s_weights_path: GPT_SoVITS/pretrained_models/s1v3.ckpt
  vits_weights_path: GPT_SoVITS/pretrained_models/v2Pro/s2Gv2Pro.pth
""".strip(),
        encoding="utf-8",
    )
    gpt, sovits = read_v2pro_base_weights(engine)
    assert gpt == "GPT_SoVITS/pretrained_models/s1v3.ckpt"
    assert sovits == "GPT_SoVITS/pretrained_models/v2Pro/s2Gv2Pro.pth"


def test_resolve_quick_clone_uses_base_not_custom_finetune(tmp_path):
    engine = tmp_path / "engine"
    cfg = engine / "GPT_SoVITS/configs"
    cfg.mkdir(parents=True)
    (cfg / "tts_infer_v2pro.yaml").write_text(
        """
v2Pro:
  t2s_weights_path: GPT_SoVITS/pretrained_models/s1v3.ckpt
  vits_weights_path: GPT_SoVITS/pretrained_models/v2Pro/s2Gv2Pro.pth
""".strip(),
        encoding="utf-8",
    )
    with patch("voice_platform.engine.infer_weights.get_settings") as gs:
        gs.return_value.engine_default_gpt_weights = ""
        gs.return_value.engine_default_sovits_weights = ""
        gs.return_value.engine_train_root = str(engine)
        pair = resolve_synthesis_weights(
            {
                "train_mode": "quick_clone",
                "engine_ref_audio_container": "/workspace/x/ref.wav",
            }
        )
    assert pair == (
        "GPT_SoVITS/pretrained_models/s1v3.ckpt",
        "GPT_SoVITS/pretrained_models/v2Pro/s2Gv2Pro.pth",
    )


def test_resolve_prefers_finetuned_metadata():
    pair = resolve_synthesis_weights(
        {
            "train_mode": "engine",
            "engine_gpt_weights": "GPT_weights_v2Pro/mine.ckpt",
            "engine_sovits_weights": "SoVITS_weights_v2Pro/mine.pth",
        }
    )
    assert pair == ("GPT_weights_v2Pro/mine.ckpt", "SoVITS_weights_v2Pro/mine.pth")

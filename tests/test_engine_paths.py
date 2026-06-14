from __future__ import annotations

from pathlib import Path

from voice_platform.engine.paths import host_path_to_container, weights_path_for_api


def test_host_path_to_container_platform_storage(monkeypatch):
    proot = Path("C:/Users/panta/Desktop/GPT")
    host = proot / "data" / "storage" / "user" / "training" / "a.wav"
    out = host_path_to_container(
        str(host),
        platform_root_path=proot,
        platform_mount="/workspace/GPT",
    )
    assert out == "/workspace/GPT/data/storage/user/training/a.wav"


def test_weights_path_for_api_from_metadata():
    gpt, sov = weights_path_for_api(
        {
            "engine_gpt_weights": "GPT_weights_v2Pro/pf_test-e4.ckpt",
            "engine_sovits_weights": "SoVITS_weights_v2Pro/pf_test_e4_s100.pth",
        }
    )
    assert gpt == "GPT_weights_v2Pro/pf_test-e4.ckpt"
    assert sov == "SoVITS_weights_v2Pro/pf_test_e4_s100.pth"


def test_weights_path_requires_both_for_api():
    gpt, sov = weights_path_for_api({"checkpoint_uri": "engine://SoVITS_weights_v2Pro/x.pth"})
    assert gpt is None and sov is None

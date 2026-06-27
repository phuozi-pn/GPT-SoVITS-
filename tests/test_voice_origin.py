from domains.voices.origin import resolve_voice_train_mode


def test_resolve_quick_clone_from_metadata():
    assert (
        resolve_voice_train_mode(
            metadata={"train_mode": "quick_clone"},
            checkpoint_uri="quick://voice/job",
        )
        == "quick_clone"
    )


def test_resolve_quick_clone_from_checkpoint():
    assert (
        resolve_voice_train_mode(
            metadata={},
            checkpoint_uri="quick://voice/job",
        )
        == "quick_clone"
    )


def test_resolve_cloud():
    assert resolve_voice_train_mode(metadata={"train_mode": "cloud"}) == "cloud"


def test_resolve_engine_from_weights():
    assert (
        resolve_voice_train_mode(
            metadata={"engine_gpt_weights": "GPT_weights/xxx.ckpt"},
            checkpoint_uri="engine://SoVITS_weights/xxx.pth",
        )
        == "engine"
    )


def test_resolve_imported():
    assert (
        resolve_voice_train_mode(
            metadata={"imported": True, "train_mode": "import_upload"},
            imported=True,
        )
        == "import_upload"
    )


def test_resolve_legacy_engine_checkpoint():
    assert (
        resolve_voice_train_mode(
            metadata={},
            checkpoint_uri="engine://SoVITS_weights/foo.pth",
        )
        == "engine"
    )

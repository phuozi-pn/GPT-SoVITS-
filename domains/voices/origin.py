"""Resolve voice version origin (quick clone vs fine-tune vs import) for API display."""

from __future__ import annotations

from typing import Any


def resolve_voice_train_mode(
    *,
    metadata: dict[str, Any] | None,
    imported: bool = False,
    checkpoint_uri: str | None = None,
) -> str:
    meta = metadata or {}
    if imported or meta.get("imported"):
        raw = str(meta.get("train_mode") or "").strip()
        if raw.startswith("import"):
            return raw
        return "import"

    explicit = str(meta.get("train_mode") or "").strip()
    if explicit:
        return explicit

    ckpt = (checkpoint_uri or "").strip()
    if ckpt.startswith("quick://"):
        return "quick_clone"
    if ckpt.startswith("engine://"):
        return "engine"
    if meta.get("engine_gpt_weights") or meta.get("engine_sovits_weights"):
        return "engine"
    if meta.get("mock"):
        return "mock"
    if ckpt:
        return "engine"
    return "unknown"

"""Prune dev voices: keep seed + one good quick-clone, delete smoke/duplicate shells."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8001"
KEEP_VOICE_IDS = frozenset(
    {
        "11111111-1111-1111-1111-111111111100",  # platform seed
        "8c7c17df-61c2-4d5c-98cf-d20ea8d2c1ef",  # 9s quick-clone (林俊杰/关键词)
        "2eed92a9-a9ea-4d6b-9e6c-04bf7d6eb9b5",  # cloud import 蛊真人-004
    }
)
DELETE_NAME_PREFIXES = ("smoke-",)
DELETE_EXACT_NAMES = frozenset({"my-voice", "我的音色", "蛊真人朗读"})


def _asset_duration(v: dict) -> float | None:
    assets = v.get("assets") or []
    if not assets:
        return None
    return assets[0].get("duration_sec")


def _created_at(v: dict) -> str:
    return v.get("created_at") or ""


def _pick_one_my_voice(voices: list[dict]) -> str | None:
    """Keep newest trained 我的音色; delete the rest."""
    candidates = [
        v
        for v in voices
        if (v.get("name") or "").strip() == "我的音色" and v.get("version_count", 0) > 0
    ]
    if not candidates:
        return None
    candidates.sort(key=_created_at, reverse=True)
    return candidates[0]["voice_id"]


def should_delete(v: dict, *, keep_my_voice_id: str | None) -> tuple[bool, str]:
    vid = v["voice_id"]
    if vid in KEEP_VOICE_IDS:
        return False, "keep: pinned"

    name = (v.get("name") or "").strip()

    if name == "我的音色" and vid == keep_my_voice_id:
        return False, "keep: newest 我的音色"

    if name in DELETE_EXACT_NAMES:
        if v.get("version_count", 0) == 0:
            return True, "empty shell"
        if name == "我的音色":
            return True, "duplicate 我的音色"
        return True, f"dev upload ({name})"

    for prefix in DELETE_NAME_PREFIXES:
        if name.lower().startswith(prefix):
            return True, f"smoke test ({name})"

    # 林俊杰 / 关键词: only pinned 9s; drop full-song (~3min) attempts
    if name in {"林俊杰", "关键词", "唱腔", "关键词-纯人声", "关键词-干声9秒"}:
        dur = _asset_duration(v)
        if dur and dur > 15:
            return True, f"superseded long upload ({dur}s)"
        if v.get("version_count", 0) == 0:
            return True, "shell without version"
        if vid not in KEEP_VOICE_IDS:
            return True, "duplicate short clone"

    if v.get("version_count", 0) == 0:
        return True, "no trained version"

    if name in {"课堂测试", "批量测试"}:
        return True, "dev upload duplicate"

    return False, "keep: active"


def main() -> int:
    dry_run = "--apply" not in sys.argv
    client = httpx.Client(base_url=BASE, timeout=60)
    voices = client.get("/api/v1/voices", params={"detail": "true"}).json()
    keep_my_voice_id = _pick_one_my_voice(voices)

    keep: list[dict] = []
    delete: list[dict] = []
    for v in voices:
        ok, reason = should_delete(v, keep_my_voice_id=keep_my_voice_id)
        row = {
            "voice_id": v["voice_id"],
            "name": v["name"],
            "version_count": v.get("version_count", 0),
            "asset_duration_sec": _asset_duration(v),
            "created_at": _created_at(v),
            "reason": reason,
        }
        (delete if ok else keep).append(row)

    report = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "dry_run": dry_run,
        "keep_my_voice_id": keep_my_voice_id,
        "keep": keep,
        "delete": delete,
    }
    out = Path(__file__).resolve().parents[1] / ".runtime" / "voice_cleanup_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"voices total={len(voices)} keep={len(keep)} delete={len(delete)} dry_run={dry_run}")
    print("\n=== KEEP ===")
    for r in keep:
        print(
            f"  {r['name']} ({r['voice_id'][:8]}…) "
            f"v={r['version_count']} dur={r['asset_duration_sec']}"
        )
    print("\n=== DELETE ===")
    for r in delete:
        print(f"  {r['name']} ({r['voice_id'][:8]}…) — {r['reason']}")

    if dry_run:
        print(f"\nDry run only. Re-run with --apply to delete. Report: {out}")
        return 0

    failed = 0
    for r in delete:
        vid = r["voice_id"]
        resp = client.delete(f"/api/v1/voices/{vid}")
        if resp.status_code not in (204, 404):
            print(f"FAIL {vid} {resp.status_code} {resp.text[:200]}")
            failed += 1
        else:
            print(f"deleted {r['name']} {vid[:8]}…")

    remaining = client.get("/api/v1/voices").json()
    print(f"\nDone. remaining={len(remaining)} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

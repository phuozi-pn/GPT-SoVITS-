#!/usr/bin/env python3
"""
Prepare aligned train segments for GPT-SoVITS fine-tune.

Run on **Linux GPU server** (AutoDL / rented cloud), not Windows local Python.

Pipeline (matches WebUI):
  1. tools/slice_audio.py  — silence-based split @ 32kHz
  2. tools/asr/funasr_asr.py — FunASR transcript per segment

Writes:
  <out-dir>/segments/*.wav
  <out-dir>/train.list          path|spk0|zh|text
  <out-dir>/manifest.json       pairs + infer_ref for platform worker
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _engine_pythonpath(cwd: Path) -> str:
    parts = [
        cwd / "GPT_SoVITS",
        cwd / "tools",
        cwd / "tools" / "asr",
        cwd / "GPT_SoVITS" / "BigVGAN",
        cwd,
    ]
    paths = [str(p) for p in parts if p.is_dir()]
    existing = os.environ.get("PYTHONPATH", "")
    if existing:
        paths.append(existing)
    return os.pathsep.join(paths)


def _run(argv: list[str], *, cwd: Path, label: str) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = _engine_pythonpath(cwd)
    print(f"[prepare_dataset] {label}: {' '.join(argv)}", flush=True)
    proc = subprocess.run(argv, cwd=str(cwd), env=env, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout[-3000:], flush=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-4000:]
        hint = ""
        if "ModuleNotFoundError" in err or "No module named" in err:
            hint = (
                "\nHint: run on a Linux GPU server (AutoDL), not Windows Python:\n"
                "  bash infra/engine/cloud/train.sh /path/to/train.wav /root/train_out job-id\n"
                "  See docs/architecture/2026-06-10-云端GPU训练指南.md\n"
            )
        raise RuntimeError(f"{label} failed ({proc.returncode}): {err}{hint}")


def _slice_defaults() -> list[str]:
    # WebUI defaults: threshold, min_length, min_interval, hop_size, max_sil_kept, _max, alpha, i_part, all_part
    return ["-34", "4000", "300", "10", "500", "0.9", "0.25", "0", "1"]


def prepare(
    *,
    engine_root: Path,
    wav_path: Path,
    out_dir: Path,
    language: str = "zh",
    speaker: str = "spk0",
    python: str | None = None,
) -> dict:
    engine_root = engine_root.resolve()
    wav_path = wav_path.resolve()
    out_dir = out_dir.resolve()
    if not (engine_root / "webui.py").is_file():
        raise RuntimeError(f"invalid engine-root: {engine_root}")
    if not wav_path.is_file():
        raise RuntimeError(f"wav not found: {wav_path}")

    segments_dir = out_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    py = python or sys.executable

    _run(
        [py, "-s", "tools/slice_audio.py", str(wav_path), str(segments_dir), *_slice_defaults()],
        cwd=engine_root,
        label="slice",
    )
    slice_files = sorted(segments_dir.glob("*.wav"))
    if not slice_files:
        raise RuntimeError("slice produced no wav files; check audio level / silence")

    asr_out = out_dir / "asr_opt"
    asr_out.mkdir(parents=True, exist_ok=True)
    _run(
        [py, "tools/asr/funasr_asr.py", "-i", str(segments_dir), "-o", str(asr_out), "-l", language],
        cwd=engine_root,
        label="asr",
    )

    asr_list = asr_out / f"{segments_dir.name}.list"
    if not asr_list.is_file():
        candidates = sorted(asr_out.glob("*.list"))
        asr_list = candidates[0] if candidates else asr_list
    if not asr_list.is_file():
        raise RuntimeError(f"ASR list not found under {asr_out}")

    pairs: list[list[str]] = []
    train_lines: list[str] = []
    for line in asr_list.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split("|", 3)
        if len(parts) < 4:
            continue
        seg_path, _name, _lang, text = parts
        text = text.strip()
        if not text:
            continue
        if not Path(seg_path).is_file():
            seg_path = str((segments_dir / Path(seg_path).name).resolve())
        if not Path(seg_path).is_file():
            continue
        pairs.append([seg_path, text])
        train_lines.append(f"{seg_path}|{speaker}|{language}|{text}")

    if not train_lines:
        raise RuntimeError("ASR produced no usable segments (empty transcripts)")

    list_file = out_dir / "train.list"
    list_file.write_text("\n".join(train_lines) + "\n", encoding="utf-8")

    manifest = {
        "segment_count": len(pairs),
        "train_list": str(list_file),
        "segments_dir": str(segments_dir),
        "pairs": pairs,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"segment_count": len(pairs), "manifest": str(manifest_path)}, ensure_ascii=False))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Slice + FunASR aligned train dataset")
    parser.add_argument("--engine-root", required=True)
    parser.add_argument("--wav", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--language", default="zh", choices=("zh", "yue"))
    parser.add_argument("--speaker", default="spk0")
    parser.add_argument(
        "--python",
        default="",
        help="Interpreter with GPT-SoVITS deps (default: current; use container python on Windows)",
    )
    args = parser.parse_args()
    try:
        prepare(
            engine_root=Path(args.engine_root),
            wav_path=Path(args.wav),
            out_dir=Path(args.out_dir),
            language=args.language,
            speaker=args.speaker,
            python=args.python or None,
        )
        return 0
    except Exception as exc:
        print(f"[prepare_dataset] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

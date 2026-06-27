#!/usr/bin/env python3
"""Batch vocal separation with Demucs; writes WAV via soundfile (no torchcodec)."""

from __future__ import annotations

import argparse
from pathlib import Path

import soundfile as sf
import torch
import torchaudio
from demucs.apply import apply_model
from demucs.pretrained import get_model


def _load_audio(in_path: Path) -> tuple[torch.Tensor, int]:
    data, sr = sf.read(str(in_path), always_2d=True)
    wav = torch.from_numpy(data.T).float()
    return wav, int(sr)


def separate_file(
    model,
    in_path: Path,
    out_path: Path,
    *,
    device: str,
) -> dict:
    wav, sr = _load_audio(in_path)
    if wav.shape[0] == 1:
        wav = wav.repeat(2, 1)
    if sr != model.samplerate:
        wav = torchaudio.functional.resample(wav, sr, model.samplerate)
        sr = model.samplerate

    with torch.no_grad():
        sources = apply_model(
            model,
            wav.unsqueeze(0),
            device=device,
            split=True,
            overlap=0.25,
            progress=False,
        )[0]

    vocals_idx = model.sources.index("vocals")
    vocals = sources[vocals_idx].mean(dim=0).cpu().numpy()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), vocals, sr, subtype="PCM_16")
    duration_sec = round(len(vocals) / sr, 2)
    return {"input": str(in_path), "output": str(out_path), "duration_sec": duration_sec, "sample_rate": sr}


def main() -> int:
    parser = argparse.ArgumentParser(description="Separate vocals from background with Demucs")
    parser.add_argument("input_dir", type=Path, help="Folder of wav/mp3/flac files")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output folder (default: <input>_vocals)",
    )
    parser.add_argument("-n", "--model", default="htdemucs", help="Demucs model name")
    parser.add_argument("--device", default="cpu", help="cpu or cuda")
    args = parser.parse_args()

    in_dir = args.input_dir.resolve()
    if not in_dir.is_dir():
        raise SystemExit(f"Not a directory: {in_dir}")

    out_dir = (args.output_dir or in_dir.with_name(in_dir.name + "_vocals")).resolve()
    exts = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
    files = sorted(p for p in in_dir.iterdir() if p.suffix.lower() in exts)
    if not files:
        raise SystemExit(f"No audio files in {in_dir}")

    device = args.device
    if device == "cuda" and not torch.cuda.is_available():
        device = "cpu"

    print(f"Model: {args.model}  device: {device}  files: {len(files)}")
    model = get_model(args.model)
    model.to(device)
    model.eval()

    results: list[dict] = []
    for i, src in enumerate(files, 1):
        dst = out_dir / f"{src.stem}_vocals.wav"
        print(f"[{i}/{len(files)}] {src.name}")
        results.append(separate_file(model, src, dst, device=device))

    total_sec = sum(r["duration_sec"] for r in results)
    print(f"Done -> {out_dir}")
    print(f"  {len(results)} files, total {total_sec:.1f}s vocal audio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

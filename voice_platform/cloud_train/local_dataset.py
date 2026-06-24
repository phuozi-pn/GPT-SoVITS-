"""Prepare aligned train dataset on local Windows before cloud upload."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from voice_platform.cloud_train.dataset_enrich import enrich_dataset_segments
from voice_platform.asr.service import AssetAsrService
from voice_platform.config import Settings, get_settings
from voice_platform.engine.dataset_slice import slice_wav_dataset, slice_wav_into_segments, wav_duration_sec
from voice_platform.engine.train_dataset import filter_pairs_by_duration, pick_infer_reference

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedLocalDataset:
    dataset_dir: Path
    segments_dir: Path
    train_list: Path
    pairs: list[tuple[str, str]]
    mode: str
    infer_ref_path: Path
    infer_ref_text: str
    segment_count: int
    segment_meta: list[dict]
    enrich_mode: str


def write_train_list(
    *,
    pairs: list[tuple[str, str]],
    list_path: Path,
    segments_prefix: str,
    speaker: str,
    language: str,
) -> None:
    """Write GPT-SoVITS train.list; paths use segments_prefix + basename."""
    prefix = segments_prefix.rstrip("/")
    lines: list[str] = []
    for seg_path, text in pairs:
        name = Path(seg_path).name
        remote = f"{prefix}/{name}"
        lines.append(f"{remote}|{speaker}|{language}|{text}")
    list_path.parent.mkdir(parents=True, exist_ok=True)
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare_local_cloud_dataset(
    *,
    wav_path: Path,
    out_dir: Path,
    ref_text: str,
    language: str | None = None,
    speaker: str = "spk0",
    use_asr: bool | None = None,
    use_llm_enrich: bool | None = None,
    asr_threshold_sec: float = 15.0,
    settings: Settings | None = None,
) -> PreparedLocalDataset:
    """Slice + align on local machine; upload only segments + train.list to cloud."""
    settings = settings or get_settings()
    language = language or settings.train_asr_language or "zh"
    ref_text = ref_text.strip()
    if not ref_text:
        raise RuntimeError("ref_text required for local dataset prep")

    wav_path = wav_path.resolve()
    out_dir = out_dir.resolve()
    segments_dir = out_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    duration = wav_duration_sec(wav_path)
    asr_service = AssetAsrService(settings)
    asr_ok = asr_service.is_available()
    use_asr = settings.train_use_asr if use_asr is None else use_asr

    if duration <= asr_threshold_sec:
        pairs = slice_wav_dataset(wav_path=wav_path, ref_text=ref_text, out_dir=segments_dir)
        mode = "manual"
    elif use_asr and asr_ok:
        seg_paths = slice_wav_into_segments(wav_path, segments_dir)
        pairs = []
        for seg in seg_paths:
            result = asr_service.transcribe_segment(seg)
            text = result.text.strip()
            if text:
                pairs.append((str(seg.resolve()), text))
        mode = "asr"
        logger.info(
            "local cloud dataset asr: %s segments from %.1fs wav",
            len(pairs),
            duration,
        )
    else:
        pairs = slice_wav_dataset(wav_path=wav_path, ref_text=ref_text, out_dir=segments_dir)
        mode = "manual_ref_bucket"
        logger.info(
            "local cloud dataset manual bucket (ASR unavailable): %.1fs wav",
            duration,
        )

    pairs = filter_pairs_by_duration(pairs)
    if not pairs:
        raise RuntimeError("local dataset prep produced no usable segments (check audio / ASR)")

    enrich_mode = "off"
    segment_meta: list[dict] = []
    if mode in ("asr", "manual_ref_bucket"):
        pairs, enrichments, enrich_mode = enrich_dataset_segments(
            pairs,
            settings=settings,
            use_llm_enrich=use_llm_enrich,
        )
        segment_meta = [e.to_dict() for e in enrichments]
        if enrich_mode != "off":
            logger.info(
                "local cloud dataset enrich mode=%s segments=%s",
                enrich_mode,
                len(segment_meta),
            )

    infer_path, infer_text = pick_infer_reference(pairs, out_dir=segments_dir)
    list_file = out_dir / "train.list"
    write_train_list(
        pairs=pairs,
        list_path=list_file,
        segments_prefix=str(segments_dir),
        speaker=speaker,
        language=language,
    )

    manifest = {
        "segment_count": len(pairs),
        "mode": mode,
        "train_list": str(list_file),
        "segments_dir": str(segments_dir),
        "pairs": pairs,
        "infer_ref": str(Path(infer_path).resolve()),
        "infer_ref_text": infer_text,
        "enrich_mode": enrich_mode,
        "segment_meta": segment_meta,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return PreparedLocalDataset(
        dataset_dir=out_dir,
        segments_dir=segments_dir,
        train_list=list_file,
        pairs=pairs,
        mode=mode,
        infer_ref_path=Path(infer_path).resolve(),
        infer_ref_text=infer_text,
        segment_count=len(pairs),
        segment_meta=segment_meta,
        enrich_mode=enrich_mode,
    )


def rewrite_train_list_for_remote(
    prepared: PreparedLocalDataset,
    *,
    remote_segments_dir: str,
    speaker: str = "spk0",
    language: str = "zh",
) -> Path:
    write_train_list(
        pairs=prepared.pairs,
        list_path=prepared.train_list,
        segments_prefix=remote_segments_dir,
        speaker=speaker,
        language=language,
    )
    return prepared.train_list

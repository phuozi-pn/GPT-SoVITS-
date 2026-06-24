from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from voice_platform.asr.base import AsrProvider, AsrResult
from voice_platform.config import Settings
from voice_platform.engine.train_dataset import trim_wav_copy

logger = logging.getLogger(__name__)

_model_cache: dict[tuple[str, str], object] = {}


class FasterWhisperAsrProvider(AsrProvider):
    name = "faster_whisper"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _model(self):
        from faster_whisper import WhisperModel

        key = (self._settings.asset_asr_model, self._settings.asset_asr_device)
        if key not in _model_cache:
            logger.info(
                "loading faster-whisper model=%s device=%s",
                self._settings.asset_asr_model,
                self._settings.asset_asr_device,
            )
            _model_cache[key] = WhisperModel(
                self._settings.asset_asr_model,
                device=self._settings.asset_asr_device,
                compute_type=self._settings.asset_asr_compute_type,
            )
        return _model_cache[key]

    def transcribe(self, wav_path: Path, *, language: str, clip_sec: float) -> AsrResult:
        clip_path = wav_path
        tmp: Path | None = None
        if clip_sec > 0:
            tmp_dir = Path(tempfile.gettempdir()) / "voice_platform_asr"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp = tmp_dir / f"{wav_path.stem}_{int(clip_sec)}s.wav"
            trim_wav_copy(wav_path, tmp, max_sec=clip_sec)
            clip_path = tmp

        try:
            model = self._model()
            segments, _info = model.transcribe(
                str(clip_path),
                language=language or None,
                vad_filter=True,
            )
            text = "".join(seg.text.strip() for seg in segments).strip()
            if not text:
                raise RuntimeError("empty transcript")
            return AsrResult(text=text, provider=self.name, clip_sec=clip_sec)
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)

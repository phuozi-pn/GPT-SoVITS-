from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import UUID, uuid4

from domains.assets.convert import ensure_wav
from domains.voices.weight_registration import EngineWeightsRegistration, register_engine_weights_version
from voice_platform.config import get_settings
from voice_platform.job.repository import VoiceRepository, VoiceVersionRepository
from voice_platform.job.schemas import ImportEngineWeightsRequest, MODEL_TAG_V2PRO, VoiceVersionSummary
from voice_platform.storage.resolve import resolve_storage_uri


class ImportServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def engine_train_root_ready() -> tuple[bool, Path | None]:
    settings = get_settings()
    root = (settings.engine_train_root or "").strip()
    if not root:
        return False, None
    path = Path(root).resolve()
    if not path.is_dir():
        return False, path
    return True, path


class EngineWeightsImportService:
    """Register GPT-SoVITS weights (on host or uploaded) as a platform VoiceVersion."""

    def __init__(self, session) -> None:
        self._session = session
        self._voices = VoiceRepository(session)
        self._versions = VoiceVersionRepository(session)
        self._settings = get_settings()

    def import_weights(
        self,
        *,
        owner_user_id: UUID,
        body: ImportEngineWeightsRequest,
    ) -> VoiceVersionSummary:
        engine_root = self._require_engine_root()
        gpt_rel = body.engine_gpt_weights.replace("\\", "/").lstrip("/")
        sovits_rel = body.engine_sovits_weights.replace("\\", "/").lstrip("/")
        self._assert_weight_files(engine_root, gpt_rel, sovits_rel)

        ref_src = self._resolve_ref_path(body)
        voice = self._resolve_voice(owner_user_id=owner_user_id, body=body)

        row = register_engine_weights_version(
            session=self._session,
            reg=EngineWeightsRegistration(
                voice_id=voice.id,
                owner_user_id=owner_user_id,
                gpt_rel=gpt_rel,
                sovits_rel=sovits_rel,
                ref_src_path=ref_src,
                ref_text=body.ref_text,
                model_tag=body.model_tag or MODEL_TAG_V2PRO,
                label=body.label.strip() or f"v{self._versions.next_version_number(voice.id)}",
                text_lang=self._settings.train_asr_language or "zh",
                text_split_method=body.text_split_method,
                temperature=body.temperature,
                speed_factor=body.speed_factor,
                top_p=body.top_p,
                extra_metadata=self._import_metadata(body),
            ),
        )
        return _version_summary(row, voice.name)

    def import_uploaded_files(
        self,
        *,
        owner_user_id: UUID,
        voice_name: str,
        ref_text: str,
        gpt_bytes: bytes,
        sovits_bytes: bytes,
        ref_bytes: bytes,
        voice_id: UUID | None = None,
        label: str = "",
        consent_id: UUID | None = None,
        voice_asset_id: UUID | None = None,
        model_tag: str = MODEL_TAG_V2PRO,
    ) -> VoiceVersionSummary:
        engine_root = self._require_engine_root()
        import_id = uuid4().hex[:12]
        gpt_rel = f"GPT_weights_v2Pro/import_{import_id}.ckpt"
        sovits_rel = f"SoVITS_weights_v2Pro/import_{import_id}.pth"
        gpt_path = engine_root / gpt_rel
        sovits_path = engine_root / sovits_rel
        gpt_path.parent.mkdir(parents=True, exist_ok=True)
        sovits_path.parent.mkdir(parents=True, exist_ok=True)
        gpt_path.write_bytes(gpt_bytes)
        sovits_path.write_bytes(sovits_bytes)

        staging = Path(self._settings.storage_root) / str(owner_user_id) / "import_refs" / import_id
        staging.mkdir(parents=True, exist_ok=True)
        ref_raw = staging / "ref_upload.wav"
        ref_raw.write_bytes(ref_bytes)
        ref_src = ensure_wav(ref_raw)

        if voice_id:
            voice = self._voices.get_voice(voice_id)
            if not voice or voice.owner_user_id != owner_user_id:
                raise ImportServiceError("VOICE_NOT_FOUND", "Voice not found", 404)
        else:
            voice = self._voices.create_voice(owner_user_id=owner_user_id, name=voice_name)

        row = register_engine_weights_version(
            session=self._session,
            reg=EngineWeightsRegistration(
                voice_id=voice.id,
                owner_user_id=owner_user_id,
                gpt_rel=gpt_rel,
                sovits_rel=sovits_rel,
                ref_src_path=ref_src,
                ref_text=ref_text,
                model_tag=model_tag,
                label=label.strip() or f"v{self._versions.next_version_number(voice.id)}",
                text_lang=self._settings.train_asr_language or "zh",
                extra_metadata={
                    "train_mode": "import_upload",
                    **({"consent_id": str(consent_id)} if consent_id else {}),
                    **({"voice_asset_id": str(voice_asset_id)} if voice_asset_id else {}),
                },
            ),
        )
        return _version_summary(row, voice.name)

    def import_from_result_json(
        self,
        *,
        owner_user_id: UUID,
        result_json_path: Path,
        ref_audio_host_path: str,
        ref_text: str,
        voice_name: str = "导入音色",
        voice_id: UUID | None = None,
        label: str = "",
    ) -> VoiceVersionSummary:
        if not result_json_path.is_file():
            raise ImportServiceError("RESULT_JSON_NOT_FOUND", f"Missing: {result_json_path}")
        result = json.loads(result_json_path.read_text(encoding="utf-8"))
        gpt_rel = str(result.get("gpt_checkpoint") or "").strip()
        sovits_rel = str(result.get("sovits_checkpoint") or "").strip()
        if not gpt_rel or not sovits_rel:
            raise ImportServiceError("RESULT_JSON_INVALID", "result.json missing gpt/sovits checkpoint paths")

        body = ImportEngineWeightsRequest(
            voice_id=voice_id,
            voice_name=voice_name,
            label=label or str(result.get("exp_name") or ""),
            engine_gpt_weights=gpt_rel,
            engine_sovits_weights=sovits_rel,
            ref_audio_host_path=ref_audio_host_path,
            ref_text=ref_text,
        )
        engine_root = self._require_engine_root()
        self._assert_weight_files(engine_root, gpt_rel, sovits_rel)
        ref_src = self._resolve_ref_path(body)
        voice = self._resolve_voice(owner_user_id=owner_user_id, body=body)
        row = register_engine_weights_version(
            session=self._session,
            reg=EngineWeightsRegistration(
                voice_id=voice.id,
                owner_user_id=owner_user_id,
                gpt_rel=gpt_rel,
                sovits_rel=sovits_rel,
                ref_src_path=ref_src,
                ref_text=ref_text,
                label=body.label.strip() or f"v{self._versions.next_version_number(voice.id)}",
                text_lang=self._settings.train_asr_language or "zh",
                extra_metadata={
                    "train_mode": "import_result_json",
                    "cloud_exp_name": result.get("exp_name"),
                    "cloud_elapsed_sec": result.get("elapsed_sec"),
                },
            ),
        )
        return _version_summary(row, voice.name)

    def _require_engine_root(self) -> Path:
        ok, path = engine_train_root_ready()
        if not ok or path is None:
            raise ImportServiceError(
                "ENGINE_ROOT_MISSING",
                "ENGINE_TRAIN_ROOT 未配置或目录不存在——请先设置本机 GPT-SoVITS 路径",
                500,
            )
        return path

    @staticmethod
    def _assert_weight_files(engine_root: Path, gpt_rel: str, sovits_rel: str) -> None:
        gpt_path = engine_root / Path(gpt_rel)
        sovits_path = engine_root / Path(sovits_rel)
        if not gpt_path.is_file():
            raise ImportServiceError("GPT_WEIGHTS_NOT_FOUND", f"找不到 GPT 权重：{gpt_rel}")
        if not sovits_path.is_file():
            raise ImportServiceError("SOVITS_WEIGHTS_NOT_FOUND", f"找不到 SoVITS 权重：{sovits_rel}")

    def _resolve_ref_path(self, body: ImportEngineWeightsRequest) -> Path:
        if body.ref_audio_storage_uri:
            path = resolve_storage_uri(body.ref_audio_storage_uri)
            return ensure_wav(path)
        if not (body.ref_audio_host_path or "").strip():
            raise ImportServiceError("REF_AUDIO_NOT_FOUND", "请提供 ref_audio_host_path 或 ref_audio_storage_uri")
        ref_src = Path(body.ref_audio_host_path).expanduser().resolve()
        if not ref_src.is_file():
            raise ImportServiceError("REF_AUDIO_NOT_FOUND", f"找不到参考音频：{ref_src}")
        return ensure_wav(ref_src)

    def _resolve_voice(self, *, owner_user_id: UUID, body: ImportEngineWeightsRequest):
        if body.voice_id:
            voice = self._voices.get_voice(body.voice_id)
            if not voice or voice.owner_user_id != owner_user_id:
                raise ImportServiceError("VOICE_NOT_FOUND", "音色不存在或无权访问", 404)
            return voice
        return self._voices.create_voice(owner_user_id=owner_user_id, name=body.voice_name)

    @staticmethod
    def _import_metadata(body: ImportEngineWeightsRequest) -> dict:
        meta: dict = {"train_mode": "import_host_path"}
        if body.consent_id:
            meta["consent_id"] = str(body.consent_id)
        if body.voice_asset_id:
            meta["voice_asset_id"] = str(body.voice_asset_id)
        return meta


def _version_summary(row, voice_name: str) -> VoiceVersionSummary:
    meta = row.metadata_json or {}
    return VoiceVersionSummary(
        voice_version_id=row.id,
        voice_id=row.voice_id,
        voice_name=voice_name,
        version=row.version,
        model_tag=row.model_tag,
        label=meta.get("label"),
        ref_text=row.ref_text,
        imported=bool(meta.get("imported")),
        created_at=row.created_at,
    )

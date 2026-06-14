from __future__ import annotations

import json
import logging
import shlex
import shutil
import subprocess
from pathlib import Path
from uuid import UUID

from voice_platform.config import get_db_session, get_settings
from voice_platform.engine.dataset_slice import slice_wav_dataset, wav_duration_sec
from voice_platform.engine.paths import host_path_to_container, platform_root
from voice_platform.engine.train_dataset import filter_pairs_by_duration, pick_infer_reference
from voice_platform.job.repository import VoiceVersionRepository
from voice_platform.job.schemas import MODEL_TAG_V2PRO, TrainPayload

logger = logging.getLogger(__name__)


class EngineTrainAdapter:
    """Runs GPT-SoVITS v2Pro fine-tune via spike_train_v2pro.py (platform Train Worker).

    Recommended production path: manual cloud GPU train (infra/engine/cloud/train.sh).
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._platform_root = platform_root()
        self._script = self._platform_root / "infra" / "engine" / "scripts" / "spike_train_v2pro.py"
        self._prepare_script = self._platform_root / "infra" / "engine" / "scripts" / "prepare_train_dataset.py"
        self._config = self._platform_root / "infra" / "engine" / "train-v2pro-spike.json"

    def _resolve_docker_container(self) -> str:
        configured = (self._settings.engine_train_docker or "").strip()
        if configured:
            proc = subprocess.run(
                ["docker", "ps", "--filter", f"name=^{configured}$", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
            )
            name = proc.stdout.strip().splitlines()
            if name:
                return name[0]
            logger.warning("ENGINE_TRAIN_DOCKER=%s not running; auto-detecting", configured)

        proc = subprocess.run(
            ["docker", "ps", "--filter", "publish=9874", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        found = proc.stdout.strip().splitlines()
        if found:
            if configured and found[0] != configured:
                logger.warning("Using engine container %s (update ENGINE_TRAIN_DOCKER in .env)", found[0])
            return found[0]
        return configured

    def run(self, *, payload: TrainPayload, owner_user_id: UUID, job_id: UUID) -> dict:
        engine_root = Path(self._settings.engine_train_root).resolve()
        if not engine_root.is_dir():
            raise RuntimeError(f"ENGINE_TRAIN_ROOT not found: {engine_root}")
        if not self._script.is_file():
            raise RuntimeError(f"Spike script missing: {self._script}")

        wav_path, ref_text = self._resolve_asset(payload)
        docker = self._resolve_docker_container()
        docker_engine = self._settings.engine_train_root_in_docker.rstrip("/")
        exp_name = f"pf_{str(job_id).replace('-', '')[:20]}"
        staging = engine_root / "logs" / "platform_staging" / str(job_id)
        staging.mkdir(parents=True, exist_ok=True)
        dataset_dir = staging / "dataset"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        segments_dir = dataset_dir / "segments"

        pairs, dataset_mode = self._prepare_dataset(
            wav_path=Path(wav_path),
            ref_text=ref_text,
            dataset_dir=dataset_dir,
            segments_dir=segments_dir,
            engine_root=engine_root,
            job_id=job_id,
        )
        pairs = filter_pairs_by_duration(pairs)
        if not pairs:
            raise RuntimeError("no usable train segments after QC (check ASR / audio levels)")
        logger.info("train dataset (%s): %s segments from %s", dataset_mode, len(pairs), wav_path)

        if docker:
            wav_dir = f"{docker_engine}/logs/platform_staging/{job_id}/dataset/segments"
        else:
            wav_dir = str(segments_dir.resolve())

        infer_host_path, ref_text_for_infer = pick_infer_reference(pairs, out_dir=segments_dir)
        lines: list[str] = []
        for host_seg, seg_text in pairs:
            seg_path = self._segment_train_path(
                host_seg,
                job_id=job_id,
                docker=docker,
                docker_engine=docker_engine,
            )
            lines.append(f"{seg_path}|spk0|{self._settings.train_asr_language}|{seg_text}")

        list_file = dataset_dir / "train.list"
        list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        wav_for_train = self._segment_train_path(
            infer_host_path,
            job_id=job_id,
            docker=docker,
            docker_engine=docker_engine,
        )
        result_file = staging / "result.json"

        argv = [
            "python",
            str(self._script),
            "--engine-root",
            str(engine_root),
            "--job-id",
            str(job_id),
            "--list-file",
            str(list_file),
            "--wav-dir",
            str(wav_dir),
            "--exp-name",
            exp_name,
            "--config",
            str(self._config),
            "--result",
            str(result_file),
        ]
        self._invoke(argv, engine_root=engine_root)

        if not result_file.is_file():
            raise RuntimeError("Spike train did not produce result.json")
        spike = json.loads(result_file.read_text(encoding="utf-8"))

        gpt_rel = spike["gpt_checkpoint"]
        sovits_rel = spike["sovits_checkpoint"]
        gpt_abs = str((engine_root / gpt_rel).resolve())
        sovits_abs = str((engine_root / sovits_rel).resolve())

        session = get_db_session()
        try:
            versions = VoiceVersionRepository(session)
            row = versions.create_version(
                voice_id=payload.voice_id,
                owner_user_id=owner_user_id,
                model_tag=payload.model_tag,
                checkpoint_uri=f"engine://{sovits_rel}",
                ref_audio_uri=wav_for_train,
                ref_text=ref_text_for_infer,
                metadata={
                    "train_job_id": str(job_id),
                    "mock": False,
                    "engine_gpt_weights": gpt_rel,
                    "engine_sovits_weights": sovits_rel,
                    "engine_gpt_path": gpt_abs,
                    "engine_sovits_path": sovits_abs,
                    "engine_ref_audio_path": wav_for_train,
                    "engine_root": str(engine_root),
                    "exp_name": exp_name,
                    "spike_elapsed_sec": spike.get("elapsed_sec"),
                    "gpt_epochs": spike.get("gpt_epochs"),
                    "sovits_epochs": spike.get("sovits_epochs"),
                    "text_lang": "zh",
                    "prompt_lang": "zh",
                    "voice_asset_id": str(payload.voice_asset_id),
                    "consent_id": str(payload.consent_id),
                    "dataset_mode": dataset_mode,
                    "train_segment_count": len(pairs),
                },
            )
            return {
                "voice_version_id": str(row.id),
                "checkpoint_uri": row.checkpoint_uri,
                "model_tag": row.model_tag or MODEL_TAG_V2PRO,
                "version": row.version,
                "engine_gpt_path": gpt_abs,
                "engine_sovits_path": sovits_abs,
                "elapsed_sec": spike.get("elapsed_sec"),
            }
        finally:
            session.close()

    def _resolve_asset(self, payload: TrainPayload) -> tuple[str, str]:
        hyper = payload.hyperparams or {}
        ref_text = hyper.get("ref_text") or self._settings.engine_train_sample_text
        if payload.asset_urls:
            uri = payload.asset_urls[0]
        else:
            uri = "engine://samples/ref_zh_zero_shot.wav"

        if uri.startswith("engine://"):
            rel = uri.removeprefix("engine://")
            path = Path(self._settings.engine_train_root) / rel
        elif uri.startswith("local://"):
            rel = uri.removeprefix("local://")
            path = self._platform_root / "infra" / "engine" / "samples" / Path(rel).name
            if not path.is_file():
                path = self._platform_root / "data" / "storage" / rel
        else:
            path = Path(uri)

        if not path.is_file():
            fallback = self._platform_root / "infra" / "engine" / "samples" / "ref_zh_zero_shot.wav"
            if fallback.is_file():
                path = fallback
            else:
                raise RuntimeError(f"Training asset not found: {uri} -> {path}")

        return str(path.resolve()), ref_text

    def _prepare_dataset(
        self,
        *,
        wav_path: Path,
        ref_text: str,
        dataset_dir: Path,
        segments_dir: Path,
        engine_root: Path,
        job_id: UUID,
    ) -> tuple[list[tuple[str, str]], str]:
        duration = wav_duration_sec(wav_path)
        use_asr = self._settings.train_use_asr and duration > 15.0
        if use_asr:
            if not self._prepare_script.is_file():
                raise RuntimeError(f"prepare script missing: {self._prepare_script}")
            argv = [
                "python",
                str(self._prepare_script),
                "--engine-root",
                str(engine_root),
                "--wav",
                str(wav_path),
                "--out-dir",
                str(dataset_dir),
                "--language",
                self._settings.train_asr_language,
            ]
            self._invoke(argv, engine_root=engine_root)
            manifest_path = dataset_dir / "manifest.json"
            if not manifest_path.is_file():
                raise RuntimeError("ASR dataset prep did not produce manifest.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            pairs = [(p, t) for p, t in manifest.get("pairs", [])]
            if not pairs:
                raise RuntimeError("ASR dataset prep produced no aligned segments")
            return pairs, "asr"

        pairs = slice_wav_dataset(wav_path=wav_path, ref_text=ref_text, out_dir=segments_dir)
        return pairs, "manual"

    def _segment_train_path(
        self,
        host_path: str,
        *,
        job_id: UUID,
        docker: str,
        docker_engine: str,
    ) -> str:
        if docker:
            return (
                f"{docker_engine}/logs/platform_staging/{job_id}/dataset/segments/"
                f"{Path(host_path).name}"
            )
        return str(Path(host_path).resolve())

    def _platform_mount_ready(self, docker: str) -> bool:
        mount = (self._settings.engine_train_platform_mount or "/workspace/GPT").rstrip("/")
        probe = f"{mount}/infra/engine/scripts/spike_train_v2pro.py"
        proc = subprocess.run(
            ["docker", "exec", docker, "test", "-f", probe],
            capture_output=True,
        )
        return proc.returncode == 0

    def _stage_scripts_in_engine_root(self, engine_root: Path) -> dict[str, str]:
        """Copy platform scripts into engine tree (bind-mounted as /workspace/GPT-SoVITS)."""
        dest_dir = engine_root / "logs" / "platform_scripts"
        dest_dir.mkdir(parents=True, exist_ok=True)
        docker_engine = self._settings.engine_train_root_in_docker.rstrip("/")
        mounts: dict[str, str] = {}
        for src in (self._script, self._prepare_script, self._config):
            if not src.is_file():
                continue
            target = dest_dir / src.name
            shutil.copy2(src, target)
            mounts[str(src)] = f"{docker_engine}/logs/platform_scripts/{src.name}"
        return mounts

    def _docker_script_paths(self, *, engine_root: Path, docker: str) -> dict[str, str]:
        if self._platform_mount_ready(docker):
            return self._platform_script_mounts()
        mount = self._settings.engine_train_platform_mount or "/workspace/GPT"
        logger.warning(
            "%s not mounted in container %s; staging scripts under %s/logs/platform_scripts",
            mount,
            docker,
            engine_root,
        )
        return self._stage_scripts_in_engine_root(engine_root)

    def _platform_script_mounts(self) -> dict[str, str]:
        mount = (self._settings.engine_train_platform_mount or str(self._platform_root)).rstrip("/")
        return {
            str(self._script): f"{mount}/infra/engine/scripts/spike_train_v2pro.py",
            str(self._prepare_script): f"{mount}/infra/engine/scripts/prepare_train_dataset.py",
            str(self._config): f"{mount}/infra/engine/train-v2pro-spike.json",
        }

    def _invoke(self, argv: list[str], *, engine_root: Path) -> None:
        docker = self._resolve_docker_container()
        script_mounts = self._docker_script_paths(engine_root=engine_root, docker=docker) if docker else {}
        if docker:
            mount = (self._settings.engine_train_platform_mount or str(self._platform_root)).rstrip("/")
            docker_engine = self._settings.engine_train_root_in_docker.rstrip("/")

            def _map_path(value: str) -> str:
                mapped = host_path_to_container(
                    value,
                    platform_root_path=self._platform_root,
                    platform_mount=mount,
                    engine_root_host=engine_root,
                    engine_root_container=docker_engine,
                )
                if mapped != value.replace("\\", "/"):
                    return mapped
                try:
                    rel = Path(value).resolve().relative_to(engine_root.resolve())
                    return f"{docker_engine}/{rel.as_posix()}"
                except ValueError:
                    return value

            mapped: list[str] = []
            for i, token in enumerate(argv):
                if token in script_mounts:
                    mapped.append(script_mounts[token])
                elif i > 0 and argv[i - 1] == "--engine-root":
                    mapped.append(docker_engine)
                elif i > 0 and argv[i - 1] in (
                    "--list-file",
                    "--wav-dir",
                    "--result",
                    "--wav",
                    "--out-dir",
                ):
                    mapped.append(_map_path(token))
                else:
                    mapped.append(token)

            cmd = " ".join(shlex.quote(a) for a in mapped)
            logger.info("docker exec train: %s", cmd)
            proc = subprocess.run(
                ["docker", "exec", docker, "bash", "-lc", cmd],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"docker train failed ({proc.returncode}): {proc.stderr[-2000:]}"
                )
            if proc.stdout:
                logger.info(proc.stdout[-2000:])
            return

        logger.info("local train: %s", " ".join(argv))
        proc = subprocess.run(argv, cwd=str(engine_root), capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"train failed ({proc.returncode}): {proc.stderr[-2000:]}")
        if proc.stdout:
            logger.info(proc.stdout[-2000:])

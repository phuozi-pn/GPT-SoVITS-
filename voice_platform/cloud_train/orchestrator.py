from __future__ import annotations

import json
import logging
import shlex
import shutil
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from voice_platform.cloud_train.local_dataset import PreparedLocalDataset, rewrite_train_list_for_remote
from voice_platform.cloud_train.remote_env import RemoteTrainEnvironment, ensure_remote_train_environment
from voice_platform.cloud_train.ssh_client import CloudTrainError, scp_from_remote, scp_to_remote, ssh_exec, upload_directory
from voice_platform.cloud_train.ssh_config import CloudSshConfig

logger = logging.getLogger(__name__)


def _write_local_progress(work: Path, **payload: object) -> None:
    """Write upload / staging info for Studio polling before remote spike starts."""
    path = work / "progress.json"
    existing: dict = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}
    existing.update(payload)
    existing["updated_at"] = time.time()
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


def _poll_remote_progress(
    cfg: CloudSshConfig,
    *,
    remote_out: str,
    local_progress: Path,
    stop: threading.Event,
    interval_sec: float = 30.0,
) -> None:
    while not stop.wait(interval_sec):
        try:
            scp_from_remote(cfg, f"{remote_out}/progress.json", local_progress)
            if local_progress.is_file():
                prog = json.loads(local_progress.read_text(encoding="utf-8"))
                logger.info(
                    "cloud_train progress phase=%s message=%s",
                    prog.get("phase"),
                    prog.get("message"),
                )
        except Exception:
            pass


def _run_remote_train_with_progress(
    cfg: CloudSshConfig,
    *,
    remote_cmd: str,
    remote_out: str,
    local_work: Path,
    timeout_sec: int,
) -> None:
    """Blocking remote train (reliable) + background progress.json polling."""
    local_progress = local_work / "progress.json"
    stop = threading.Event()
    poller = threading.Thread(
        target=_poll_remote_progress,
        kwargs={
            "cfg": cfg,
            "remote_out": remote_out,
            "local_progress": local_progress,
            "stop": stop,
        },
        daemon=True,
    )
    poller.start()
    try:
        ro = shlex.quote(remote_out)
        ssh_exec(
            cfg,
            f"mkdir -p {ro} && {remote_cmd}",
            timeout_sec=timeout_sec,
        )
    except CloudTrainError as exc:
        tail = ""
        try:
            tail = ssh_exec(
                cfg,
                f"tail -80 {ro}/remote.log 2>/dev/null || tail -80 {ro}/../dataset/../out/remote.log 2>/dev/null || true",
                timeout_sec=60,
            )
        except Exception:
            pass
        if tail.strip():
            raise CloudTrainError(f"{exc}; remote log tail: {tail[-2500:]}") from exc
        raise
    finally:
        stop.set()
        poller.join(timeout=5)
        try:
            scp_from_remote(cfg, f"{remote_out}/progress.json", local_progress)
        except Exception:
            pass


@dataclass(frozen=True)
class CloudTrainOutcome:
    result: dict
    local_work_dir: Path
    gpt_local: Path
    sovits_local: Path
    ref_wav_local: Path
    infer_ref_text: str | None = None
    dataset_mode: str | None = None
    remote_work_dir: str | None = None
    remote_dataset_dir: str | None = None
    segment_count: int | None = None


def _pull_remote_infer_reference(
    cfg: CloudSshConfig,
    *,
    remote_out: str,
    work: Path,
    fallback_wav: Path,
    max_segments: int = 24,
) -> tuple[Path, str | None]:
    """After remote train.sh, pull ASR segments and pick a 3–10s synthesis ref."""
    from voice_platform.engine.train_dataset import parse_train_list, pick_infer_reference

    remote_dataset = f"{remote_out.rstrip('/')}/dataset"
    train_list_local = work / "remote_train.list"
    try:
        scp_from_remote(cfg, f"{remote_dataset}/train.list", train_list_local)
    except Exception as exc:
        logger.warning("cloud_train remote train.list unavailable: %s", exc)
        return fallback_wav, None
    if not train_list_local.is_file():
        return fallback_wav, None
    if not pairs_remote:
        return fallback_wav, None

    segments_local = work / "infer_segments"
    segments_local.mkdir(parents=True, exist_ok=True)
    local_pairs: list[tuple[str, str]] = []
    for remote_path, text in pairs_remote[:max_segments]:
        name = Path(remote_path).name
        local_seg = segments_local / name
        if not local_seg.is_file():
            try:
                scp_from_remote(cfg, f"{remote_dataset}/segments/{name}", local_seg)
            except Exception:
                continue
        if local_seg.is_file():
            local_pairs.append((str(local_seg.resolve()), text))

    if not local_pairs:
        return fallback_wav, None

    try:
        infer_path, infer_text = pick_infer_reference(local_pairs, out_dir=segments_local)
        infer_ref = work / "infer_ref.wav"
        shutil.copy2(infer_path, infer_ref)
        logger.info(
            "cloud_train infer ref from remote dataset segments=%s text=%r",
            len(local_pairs),
            infer_text[:48] if infer_text else "",
        )
        return infer_ref, infer_text
    except Exception as exc:
        logger.warning("cloud_train pick infer ref failed: %s", exc)
        return fallback_wav, None


class CloudTrainOrchestrator:
    """Upload wav or pre-built dataset → remote train → pull weights + result.json."""

    def __init__(self, ssh_config: CloudSshConfig, *, storage_root: str) -> None:
        self._ssh = ssh_config
        self._storage_root = storage_root

    def run(
        self,
        *,
        local_wav: Path,
        job_id: str,
        prepared_dataset: PreparedLocalDataset | None = None,
        remote_env: RemoteTrainEnvironment | None = None,
    ) -> CloudTrainOutcome:
        if not local_wav.is_file():
            raise CloudTrainError(f"Source wav missing: {local_wav}")

        work = Path(self._storage_root) / "cloud_train" / job_id
        work.mkdir(parents=True, exist_ok=True)

        cfg = self._ssh
        remote_work = f"{cfg.remote_work_dir.rstrip('/')}/{job_id}"
        remote_out = f"{remote_work}/out"
        remote_dataset: str | None = None
        segment_count: int | None = None

        env = remote_env or ensure_remote_train_environment(
            cfg,
            local_dataset_prep=prepared_dataset is not None,
        )
        engine_root = env.engine_root
        platform_root = env.platform_root
        remote_python = env.python
        py_export = f"export CLOUD_TRAIN_PYTHON={shlex.quote(remote_python)}"

        ssh_exec(cfg, f"mkdir -p {shlex.quote(remote_work)}")

        if prepared_dataset is not None:
            remote_dataset = f"{remote_work}/dataset"
            remote_segments = f"{remote_dataset}/segments"
            rewrite_train_list_for_remote(
                prepared_dataset,
                remote_segments_dir=remote_segments,
            )
            logger.info(
                "cloud_train upload prepared dataset job_id=%s segments=%s mode=%s",
                job_id,
                prepared_dataset.segment_count,
                prepared_dataset.mode,
            )
            upload_directory(cfg, prepared_dataset.dataset_dir, remote_dataset)
            segment_count = prepared_dataset.segment_count
            _write_local_progress(
                work,
                phase="upload_done",
                message=f"已上传 {segment_count} 段至远端 dataset",
                remote_work_dir=remote_work,
                remote_dataset_dir=remote_dataset,
                remote_segments_dir=remote_segments,
                segment_count=segment_count,
                dataset_mode=prepared_dataset.mode,
            )
            train_script = f"{platform_root.rstrip('/')}/infra/engine/cloud/train_from_dataset.sh"
            remote_cmd = " ".join(
                [
                    f"export PATH=/root/miniconda3/bin:/usr/local/bin:/usr/bin:$PATH",
                    f"export ENGINE_ROOT={shlex.quote(engine_root)}",
                    f"export PLATFORM_ROOT={shlex.quote(platform_root)}",
                    "export is_half=False",
                    py_export,
                    "&&",
                    "bash",
                    shlex.quote(train_script),
                    shlex.quote(remote_dataset),
                    shlex.quote(remote_out),
                    shlex.quote(job_id),
                ]
            )
            ref_local = work / "infer_ref.wav"
            if not ref_local.exists():
                shutil.copy2(prepared_dataset.infer_ref_path, ref_local)
            dataset_mode = prepared_dataset.mode
        else:
            remote_wav = f"{remote_work}/source.wav"
            train_script = f"{platform_root.rstrip('/')}/infra/engine/cloud/train.sh"
            scp_to_remote(cfg, local_wav, remote_wav)
            _write_local_progress(
                work,
                phase="upload_done",
                message="整段干声已上传，远端将切分并训练",
                remote_work_dir=remote_work,
                remote_source_wav=remote_wav,
            )
            remote_cmd = " ".join(
                [
                    f"export PATH=/root/miniconda3/bin:/usr/local/bin:/usr/bin:$PATH",
                    f"export ENGINE_ROOT={shlex.quote(engine_root)}",
                    f"export PLATFORM_ROOT={shlex.quote(platform_root)}",
                    f"export TRAIN_ASR_LANGUAGE={shlex.quote('zh')}",
                    "export is_half=False",
                    py_export,
                    "&&",
                    "bash",
                    shlex.quote(train_script),
                    shlex.quote(remote_wav),
                    shlex.quote(remote_out),
                    shlex.quote(job_id),
                ]
            )
            ref_local = work / "source.wav"
            if not ref_local.exists():
                shutil.copy2(local_wav, ref_local)
            dataset_mode = None

        logger.info("cloud_train remote job_id=%s local_dataset=%s", job_id, bool(prepared_dataset))
        _run_remote_train_with_progress(
            cfg,
            remote_cmd=remote_cmd,
            remote_out=remote_out,
            local_work=work,
            timeout_sec=int(cfg.timeout_sec or 7200),
        )

        result_path = work / "result.json"
        scp_from_remote(cfg, f"{remote_out}/result.json", result_path)
        result = json.loads(result_path.read_text(encoding="utf-8"))

        gpt_rel = result.get("gpt_checkpoint")
        sovits_rel = result.get("sovits_checkpoint")
        if not gpt_rel or not sovits_rel:
            raise CloudTrainError(f"result.json missing checkpoints: {result}")

        remote_engine = engine_root.rstrip("/")
        gpt_local = work / Path(str(gpt_rel)).name
        sovits_local = work / Path(str(sovits_rel)).name
        scp_from_remote(cfg, f"{remote_engine}/{gpt_rel}", gpt_local)
        scp_from_remote(cfg, f"{remote_engine}/{sovits_rel}", sovits_local)

        infer_ref_text: str | None = None
        if prepared_dataset is not None:
            infer_ref_text = prepared_dataset.infer_ref_text
        else:
            ref_local, infer_ref_text = _pull_remote_infer_reference(
                cfg,
                remote_out=remote_out,
                work=work,
                fallback_wav=ref_local,
            )

        return CloudTrainOutcome(
            result=result,
            local_work_dir=work,
            gpt_local=gpt_local,
            sovits_local=sovits_local,
            ref_wav_local=ref_local,
            infer_ref_text=infer_ref_text,
            dataset_mode=dataset_mode,
            remote_work_dir=remote_work,
            remote_dataset_dir=remote_dataset,
            segment_count=segment_count,
        )

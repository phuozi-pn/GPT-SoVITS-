#!/usr/bin/env python3
"""
GPT-SoVITS v2Pro fine-tune spike orchestrator.

Must run with --engine-root pointing at upstream GPT-SoVITS clone (pinned 20250606v2pro).
Typical (inside Docker container):

  python /path/to/GPT/infra/engine/scripts/spike_train_v2pro.py \\
    --engine-root /workspace/GPT-SoVITS \\
    --job-id spike-001 \\
    --list-file /workspace/GPT-SoVITS/samples/train.list \\
    --wav-dir /workspace/GPT-SoVITS/samples \\
    --exp-name platform_spike_001 \\
    --config /workspace/GPT/infra/engine/train-v2pro-spike.json \\
    --result /tmp/spike_result.json
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _load_config(path: Path | None) -> dict:
    defaults = {
        "version": "v2Pro",
        "gpt_epochs": 4,
        "sovits_epochs": 4,
        "batch_size": 4,
        "gpt_batch_size": 4,
        "save_every_epoch": 4,
        "sovits_save_every_epoch": 4,
        "text_low_lr_rate": 0.4,
        "is_half": False,
        "gpu": "0",
    }
    if path and path.is_file():
        defaults.update(json.loads(path.read_text(encoding="utf-8")))
    return defaults


def _resolve_is_half(cfg: dict) -> bool:
    """FP32 cloud fine-tune matches successful AutoDL runs; FP16 can yield near-silent TTS."""
    if "is_half" in os.environ:
        return os.environ.get("is_half", "false").lower() == "true"
    raw = cfg.get("is_half", False)
    if isinstance(raw, bool):
        return raw
    return str(raw).lower() in ("1", "true", "yes")


def _engine_pythonpath(cwd: Path) -> str:
    """Match webui.py users.pth so `from text.cleaner` resolves under GPT_SoVITS/."""
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


def _merge_env(cwd: Path, extra: dict | None = None) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = _engine_pythonpath(cwd)
    if extra:
        env.update(extra)
    return env


def _run(cmd: str, *, cwd: Path, env: dict | None = None, label: str = "") -> None:
    print(f"[spike_train] {label}: {cmd}", flush=True)
    proc = subprocess.run(cmd, shell=True, cwd=str(cwd), env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {proc.returncode}")


def _write_progress(result_path: Path, *, phase: str, message: str, **extra: object) -> None:
    prog = Path(result_path).parent / "progress.json"
    payload = {
        "phase": phase,
        "message": message,
        "updated_at": time.time(),
        **extra,
    }
    prog.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _latest_file(root: Path, pattern: str) -> Path | None:
    files = sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _merge_1a_text(opt_dir: Path, all_parts: int = 1) -> None:
    """WebUI merges 2-name2text-{i}.txt → 2-name2text.txt after 1A."""
    lines: list[str] = []
    for i_part in range(all_parts):
        part = opt_dir / f"2-name2text-{i_part}.txt"
        if not part.is_file():
            raise RuntimeError(f"1A output missing: {part}")
        content = part.read_text(encoding="utf-8").strip("\n")
        if content:
            lines.extend(content.split("\n"))
        part.unlink()
    if not lines:
        raise RuntimeError("1A produced empty 2-name2text")
    (opt_dir / "2-name2text.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _merge_1c_semantic(opt_dir: Path, all_parts: int = 1) -> None:
    """WebUI merges 6-name2semantic-{i}.tsv → 6-name2semantic.tsv after 1C."""
    rows = ["item_name\tsemantic_audio"]
    for i_part in range(all_parts):
        part = opt_dir / f"6-name2semantic-{i_part}.tsv"
        if not part.is_file():
            raise RuntimeError(f"1C output missing: {part}")
        content = part.read_text(encoding="utf-8").strip("\n")
        if content:
            rows.extend(content.split("\n"))
        part.unlink()
    if len(rows) < 2:
        raise RuntimeError("1C produced empty semantic table")
    (opt_dir / "6-name2semantic.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _validate_preprocess(opt_dir: Path, version: str) -> None:
    for name in ("2-name2text.txt", "6-name2semantic.tsv"):
        path = opt_dir / name
        if not path.is_file() or path.stat().st_size < 10:
            raise RuntimeError(f"Missing or empty preprocess artifact: {path}")
    if "Pro" in version:
        sv_dir = opt_dir / "7-sv_cn"
        sv_files = list(sv_dir.glob("*.pt")) if sv_dir.is_dir() else []
        if not sv_files:
            raise RuntimeError(
                f"Missing SV embeddings in {sv_dir} (1B-sv failed; apply train torchaudio patch)"
            )


def preprocess_1abc(
    *,
    cwd: Path,
    python_exec: str,
    version: str,
    list_file: Path,
    wav_dir: Path,
    exp_name: str,
    gpu: str,
    is_half: bool,
    clean: bool,
) -> Path:
    opt_dir = cwd / "logs" / exp_name
    if clean and opt_dir.exists():
        shutil.rmtree(opt_dir)
    opt_dir.mkdir(parents=True, exist_ok=True)

    bert = "GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large"
    ssl = "GPT_SoVITS/pretrained_models/chinese-hubert-base"
    s2g = "GPT_SoVITS/pretrained_models/v2Pro/s2Gv2Pro.pth"
    sv_path = "GPT_SoVITS/pretrained_models/sv/pretrained_eres2netv2w24s4ep4.ckpt"
    s2config = "GPT_SoVITS/configs/s2v2Pro.json"

    base_env = _merge_env(
        cwd,
        {
            "inp_text": str(list_file.resolve()),
            "inp_wav_dir": str(wav_dir.resolve()),
            "exp_name": exp_name,
            "opt_dir": str(opt_dir.resolve()),
            "bert_pretrained_dir": bert,
            "cnhubert_base_dir": ssl,
            "pretrained_s2G": s2g,
            "pretrained_s2G_path": s2g,
            "s2config_path": s2config,
            "sv_path": sv_path,
            "is_half": str(is_half),
            "version": version,
            "i_part": "0",
            "all_parts": "1",
            "_CUDA_VISIBLE_DEVICES": gpu,
        },
    )

    all_parts = int(base_env["all_parts"])
    py = python_exec
    _run(f'"{py}" GPT_SoVITS/prepare_datasets/1-get-text.py', cwd=cwd, env=base_env, label="1A")
    _merge_1a_text(opt_dir, all_parts=all_parts)
    _run(f'"{py}" GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py', cwd=cwd, env=base_env, label="1B")
    if "Pro" in version:
        _run(f'"{py}" GPT_SoVITS/prepare_datasets/2-get-sv.py', cwd=cwd, env=base_env, label="1B-sv")
    _run(f'"{py}" GPT_SoVITS/prepare_datasets/3-get-semantic.py', cwd=cwd, env=base_env, label="1C")
    _merge_1c_semantic(opt_dir, all_parts=all_parts)
    _validate_preprocess(opt_dir, version)
    return opt_dir


def train_gpt(
    *,
    cwd: Path,
    python_exec: str,
    opt_dir: Path,
    exp_name: str,
    cfg: dict,
    is_half: bool,
) -> None:
    import yaml

    s1_yaml = cwd / "GPT_SoVITS/configs/s1longer-v2.yaml"
    data = yaml.safe_load(s1_yaml.read_text(encoding="utf-8"))
    batch_size = cfg["gpt_batch_size"]
    if not is_half:
        data["train"]["precision"] = "32"
        batch_size = max(1, batch_size // 2)
    data["train"]["batch_size"] = batch_size
    data["train"]["epochs"] = cfg["gpt_epochs"]
    data["pretrained_s1"] = "GPT_SoVITS/pretrained_models/s1v3.ckpt"
    data["train"]["save_every_n_epoch"] = cfg["save_every_epoch"]
    data["train"]["if_save_every_weights"] = True
    data["train"]["if_save_latest"] = True
    data["train"]["if_dpo"] = False
    data["train"]["half_weights_save_dir"] = "GPT_weights_v2Pro"
    data["train"]["exp_name"] = exp_name
    data["train_semantic_path"] = str(opt_dir / "6-name2semantic.tsv")
    data["train_phoneme_path"] = str(opt_dir / "2-name2text.txt")
    data["output_dir"] = str(opt_dir / f"logs_s1_{cfg['version']}")

    (cwd / "GPT_weights_v2Pro").mkdir(exist_ok=True)
    s1_out = opt_dir / f"logs_s1_{cfg['version']}"
    s1_out.mkdir(parents=True, exist_ok=True)
    ckpt_dir = s1_out / "ckpt"
    if ckpt_dir.is_dir():
        # Spike always trains GPT from scratch; stale ckpt triggers PL resume + torch weights_only errors.
        shutil.rmtree(ckpt_dir)

    tmp = cwd / "TEMP"
    tmp.mkdir(exist_ok=True)
    tmp_config = tmp / f"platform_s1_{exp_name}.yaml"
    tmp_config.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    env = _merge_env(
        cwd,
        {
            "_CUDA_VISIBLE_DEVICES": str(cfg["gpu"]),
            "hz": "25hz",
            "version": cfg["version"],
        },
    )
    _run(
        f'"{python_exec}" GPT_SoVITS/s1_train.py --config_file "{tmp_config}"',
        cwd=cwd,
        env=env,
        label="GPT-s1",
    )


def train_sovits(
    *,
    cwd: Path,
    python_exec: str,
    opt_dir: Path,
    exp_name: str,
    cfg: dict,
    is_half: bool,
) -> None:
    s2_json_path = cwd / "GPT_SoVITS/configs/s2v2Pro.json"
    data = json.loads(s2_json_path.read_text(encoding="utf-8"))
    batch_size = cfg["batch_size"]
    if not is_half:
        data["train"]["fp16_run"] = False
        batch_size = max(1, batch_size // 2)
    data["train"]["batch_size"] = batch_size
    data["train"]["epochs"] = cfg["sovits_epochs"]
    data["train"]["text_low_lr_rate"] = cfg["text_low_lr_rate"]
    data["train"]["pretrained_s2G"] = "GPT_SoVITS/pretrained_models/v2Pro/s2Gv2Pro.pth"
    data["train"]["pretrained_s2D"] = "GPT_SoVITS/pretrained_models/v2Pro/s2Dv2Pro.pth"
    data["train"]["if_save_latest"] = True
    data["train"]["if_save_every_weights"] = True
    data["train"]["save_every_epoch"] = cfg["sovits_save_every_epoch"]
    data["train"]["gpu_numbers"] = str(cfg["gpu"])
    data["train"]["grad_ckpt"] = False
    data["train"]["lora_rank"] = 32
    data["model"]["version"] = cfg["version"]
    data["data"]["exp_dir"] = data["s2_ckpt_dir"] = str(opt_dir)
    data["save_weight_dir"] = "SoVITS_weights_v2Pro"
    data["name"] = exp_name
    data["version"] = cfg["version"]

    (cwd / "SoVITS_weights_v2Pro").mkdir(exist_ok=True)
    (opt_dir / f"logs_s2_{cfg['version']}").mkdir(parents=True, exist_ok=True)

    tmp = cwd / "TEMP"
    tmp.mkdir(exist_ok=True)
    tmp_config = tmp / f"platform_s2_{exp_name}.json"
    tmp_config.write_text(json.dumps(data), encoding="utf-8")

    env = _merge_env(cwd, {"version": cfg["version"], "_CUDA_VISIBLE_DEVICES": str(cfg["gpu"])})
    _run(
        f'"{python_exec}" GPT_SoVITS/s2_train.py --config "{tmp_config}"',
        cwd=cwd,
        env=env,
        label="SoVITS-s2",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="GPT-SoVITS v2Pro platform train spike")
    parser.add_argument("--engine-root", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--list-file", required=True, help=".list file: wav|spk|lang|text")
    parser.add_argument("--wav-dir", required=True)
    parser.add_argument("--exp-name", required=True)
    parser.add_argument("--config", default="")
    parser.add_argument("--result", required=True)
    parser.add_argument(
        "--from-step",
        choices=("all", "gpt", "sovits"),
        default="all",
        help="Resume from a step after partial failure (default: all)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete logs/<exp_name> before preprocess (full restart)",
    )
    args = parser.parse_args()

    engine_root = Path(args.engine_root).resolve()
    if not (engine_root / "webui.py").is_file():
        print(f"engine-root invalid: {engine_root}", file=sys.stderr)
        return 1

    cfg = _load_config(Path(args.config) if args.config else None)
    is_half = _resolve_is_half(cfg)
    python_exec = sys.executable
    result_path = Path(args.result).resolve()
    result_path.parent.mkdir(parents=True, exist_ok=True)

    _write_progress(
        result_path,
        phase="starting",
        message="准备训练",
        gpt_epochs=cfg["gpt_epochs"],
        sovits_epochs=cfg["sovits_epochs"],
        job_id=args.job_id,
    )

    os.chdir(engine_root)
    os.environ["version"] = cfg["version"]
    os.environ["PYTHONPATH"] = _engine_pythonpath(engine_root)
    t0 = time.time()
    opt_dir = engine_root / "logs" / args.exp_name

    if args.from_step == "all":
        t_phase = time.time()
        _write_progress(result_path, phase="preprocess_running", message="预处理中（1A→1B→1C）")
        opt_dir = preprocess_1abc(
            cwd=engine_root,
            python_exec=python_exec,
            version=cfg["version"],
            list_file=Path(args.list_file).resolve(),
            wav_dir=Path(args.wav_dir).resolve(),
            exp_name=args.exp_name,
            gpu=str(cfg["gpu"]),
            is_half=is_half,
            clean=args.clean,
        )
        _write_progress(
            result_path,
            phase="preprocess_done",
            message=f"预处理完成 · {time.time() - t_phase:.0f}s",
        )
        t_phase = time.time()
        _write_progress(
            result_path,
            phase="gpt_running",
            message=f"GPT 微调中（{cfg['gpt_epochs']} epoch）",
            gpt_epochs=cfg["gpt_epochs"],
        )
        train_gpt(
            cwd=engine_root,
            python_exec=python_exec,
            opt_dir=opt_dir,
            exp_name=args.exp_name,
            cfg=cfg,
            is_half=is_half,
        )
        _write_progress(
            result_path,
            phase="gpt_done",
            message=f"GPT 完成 · {cfg['gpt_epochs']} epoch · {time.time() - t_phase:.0f}s",
            gpt_epochs=cfg["gpt_epochs"],
        )
    elif args.from_step == "gpt":
        if args.clean and opt_dir.exists():
            shutil.rmtree(opt_dir)
        opt_dir.mkdir(parents=True, exist_ok=True)
        _validate_preprocess(opt_dir, cfg["version"])
        train_gpt(
            cwd=engine_root,
            python_exec=python_exec,
            opt_dir=opt_dir,
            exp_name=args.exp_name,
            cfg=cfg,
            is_half=is_half,
        )
    else:
        if not opt_dir.is_dir():
            raise RuntimeError(f"Missing experiment dir for --from-step sovits: {opt_dir}")
        _validate_preprocess(opt_dir, cfg["version"])

    t_phase = time.time()
    _write_progress(
        result_path,
        phase="sovits_running",
        message=f"SoVITS 微调中（{cfg['sovits_epochs']} epoch）",
        sovits_epochs=cfg["sovits_epochs"],
    )
    train_sovits(
        cwd=engine_root,
        python_exec=python_exec,
        opt_dir=opt_dir,
        exp_name=args.exp_name,
        cfg=cfg,
        is_half=is_half,
    )
    _write_progress(
        result_path,
        phase="sovits_done",
        message=f"SoVITS 完成 · {cfg['sovits_epochs']} epoch · {time.time() - t_phase:.0f}s",
        sovits_epochs=cfg["sovits_epochs"],
    )

    gpt_weight = _latest_file(engine_root / "GPT_weights_v2Pro", f"{args.exp_name}*.ckpt")
    sovits_weight = _latest_file(engine_root / "SoVITS_weights_v2Pro", f"{args.exp_name}*.pth")
    if not gpt_weight or not sovits_weight:
        raise RuntimeError("Training finished but output weights not found")

    elapsed = round(time.time() - t0, 1)
    result = {
        "job_id": args.job_id,
        "exp_name": args.exp_name,
        "model_tag": cfg.get("model_tag", "gsv-v2pro-20250606"),
        "gpt_checkpoint": str(gpt_weight.relative_to(engine_root)).replace("\\", "/"),
        "sovits_checkpoint": str(sovits_weight.relative_to(engine_root)).replace("\\", "/"),
        "elapsed_sec": elapsed,
        "gpt_epochs": cfg["gpt_epochs"],
        "sovits_epochs": cfg["sovits_epochs"],
        "version": cfg["version"],
    }
    Path(args.result).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_progress(
        result_path,
        phase="done",
        message=f"全部完成 · 远端耗时 {elapsed:.0f}s",
        elapsed_sec=elapsed,
        gpt_epochs=cfg["gpt_epochs"],
        sovits_epochs=cfg["sovits_epochs"],
    )
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[spike_train] ERROR: {exc}", file=sys.stderr)
        raise

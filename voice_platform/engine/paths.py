from __future__ import annotations

from pathlib import Path

from voice_platform.config import get_settings


def platform_root() -> Path:
    return Path(__file__).resolve().parents[2]


def host_path_to_container(
    host_path: str,
    *,
    platform_root_path: Path | None = None,
    platform_mount: str | None = None,
    engine_root_host: Path | None = None,
    engine_root_container: str | None = None,
) -> str:
    """Map a Windows/host path to in-container path when platform/engine are mounted."""
    if not host_path:
        return host_path
    normalized = host_path.replace("\\", "/")
    if normalized.startswith("/workspace/"):
        return normalized

    settings = get_settings()
    proot = (platform_root_path or platform_root()).resolve()
    pmount = (platform_mount or settings.engine_train_platform_mount or "/workspace/GPT").rstrip("/")
    eroot = (engine_root_host or Path(settings.engine_train_root)).resolve() if settings.engine_train_root else None
    econtainer = (engine_root_container or settings.engine_train_root_in_docker or "/workspace/GPT-SoVITS").rstrip("/")

    p = Path(host_path).resolve()
    try:
        rel = p.relative_to(proot)
        return f"{pmount}/{rel.as_posix()}"
    except ValueError:
        pass
    if eroot:
        try:
            rel = p.relative_to(eroot)
            return f"{econtainer}/{rel.as_posix()}"
        except ValueError:
            pass
    return normalized


def weights_path_for_api(meta: dict) -> tuple[str | None, str | None]:
    """Relative GPT/SoVITS paths for api_v2 set_*_weights."""
    gpt = meta.get("engine_gpt_weights")
    sovits = meta.get("engine_sovits_weights")
    if not sovits:
        uri = meta.get("checkpoint_uri") or ""
        if uri.startswith("engine://"):
            sovits = uri.removeprefix("engine://")
    if gpt and sovits:
        return str(gpt), str(sovits)
    gpt_abs = meta.get("engine_gpt_path")
    sovits_abs = meta.get("engine_sovits_path")
    if gpt_abs and sovits_abs:
        return _abs_to_engine_relative(gpt_abs), _abs_to_engine_relative(sovits_abs)
    return None, None


def _abs_to_engine_relative(abs_path: str) -> str:
    p = Path(abs_path)
    parts = p.parts
    for marker in ("GPT_weights_v2Pro", "SoVITS_weights_v2Pro"):
        if marker in parts:
            idx = parts.index(marker)
            return "/".join(parts[idx:])
    return p.name

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
EXAMPLE_PROFILE_DIR = ROOT_DIR / "project-config" / "models"
ENV_FILE = ROOT_DIR / ".env"
HF_CACHE_ROOT = Path.home() / ".cache" / "huggingface" / "hub"
DEFAULT_LOG_ROTATION_DAYS = 5
DEFAULT_STORAGE_PATH = "storage"
DEFAULT_LOG_PROFILE_PATH = "logs/profiles"

_ENV_CACHE_PATH: Path | None = None
_ENV_CACHE_MTIME_NS: int | None = None
_ENV_CACHE_VALUES: dict[str, str] | None = None


def clear_env_cache() -> None:
    global _ENV_CACHE_PATH, _ENV_CACHE_MTIME_NS, _ENV_CACHE_VALUES
    _ENV_CACHE_PATH = None
    _ENV_CACHE_MTIME_NS = None
    _ENV_CACHE_VALUES = None


def get_storage_root(env: dict[str, str] | None = None) -> Path:
    values = env if env is not None else parse_env_file()
    configured = values.get("STORAGE_PATH", "").strip()
    raw_path = configured or DEFAULT_STORAGE_PATH

    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        storage_root = candidate
    else:
        storage_root = (ROOT_DIR / candidate).resolve()

    storage_root.mkdir(parents=True, exist_ok=True)
    return storage_root


def get_local_profile_dir(env: dict[str, str] | None = None) -> Path:
    path = get_storage_root(env) / "project-local-config" / "profiles" / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_pid_dir(env: dict[str, str] | None = None) -> Path:
    path = get_storage_root(env) / "project-local-config" / "pids"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_runtime_dirs() -> None:
    get_local_profile_dir()
    EXAMPLE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    get_pid_dir()


def parse_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    global _ENV_CACHE_PATH, _ENV_CACHE_MTIME_NS, _ENV_CACHE_VALUES

    resolved_path = path.resolve()
    if not resolved_path.exists():
        if _ENV_CACHE_PATH == resolved_path:
            clear_env_cache()
        return {}

    mtime_ns = resolved_path.stat().st_mtime_ns
    if (
        _ENV_CACHE_PATH == resolved_path
        and _ENV_CACHE_MTIME_NS == mtime_ns
        and _ENV_CACHE_VALUES is not None
    ):
        merged = dict(_ENV_CACHE_VALUES)
        for key, value in os.environ.items():
            merged[key] = value
        return merged

    values = dotenv_values(resolved_path)
    env: dict[str, str] = {}
    for key, value in values.items():
        if key is None or value is None:
            continue
        env[str(key)] = str(value)

    _ENV_CACHE_PATH = resolved_path
    _ENV_CACHE_MTIME_NS = mtime_ns
    _ENV_CACHE_VALUES = dict(env)

    merged = dict(env)
    for key, value in os.environ.items():
        merged[key] = value

    return merged


def get_log_rotation_days(env: dict[str, str] | None = None) -> int:
    values = env if env is not None else parse_env_file()
    raw_value = values.get("LOG_ROTATION_DAYS", "").strip()
    if not raw_value:
        return DEFAULT_LOG_ROTATION_DAYS

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(
            "LOG_ROTATION_DAYS must be an integer in .env. "
            "Use 0 or a negative number to keep logs forever, "
            "or a positive number for retention days."
        ) from exc


def get_profile_log_dir(env: dict[str, str] | None = None) -> Path:
    values = env if env is not None else parse_env_file()
    configured = values.get("LOG_PROFILE_PATH", "").strip()
    if not configured:
        log_dir = get_storage_root(values) / DEFAULT_LOG_PROFILE_PATH
    else:
        candidate = Path(configured).expanduser()
        if candidate.is_absolute():
            log_dir = candidate
        else:
            log_dir = (ROOT_DIR / candidate).resolve()

    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _resolve_env_vars(value: str, env: dict[str, str]) -> str:
    pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return env.get(key, "")

    return pattern.sub(replace, value)


def resolve_profile_values(obj: Any, env: dict[str, str]) -> Any:
    if isinstance(obj, dict):
        return {k: resolve_profile_values(v, env) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_profile_values(v, env) for v in obj]
    if isinstance(obj, str):
        return _resolve_env_vars(obj, env)
    return obj


def _candidate_profile_paths(profile_name: str) -> list[Path]:
    candidate = Path(profile_name)
    candidates: list[Path] = []
    local_profile_dir = get_local_profile_dir()

    if candidate.is_absolute():
        candidates.append(candidate)
    else:
        candidates.append(local_profile_dir / candidate)
        if candidate.suffix not in {".yaml", ".yml"}:
            candidates.append(local_profile_dir / f"{profile_name}.yaml")
            candidates.append(local_profile_dir / f"{profile_name}.yml")

    return candidates


def resolve_profile_path(profile_name: str) -> Path:
    local_profile_dir = get_local_profile_dir()
    for candidate in _candidate_profile_paths(profile_name):
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"Profile '{profile_name}' was not found in {local_profile_dir}."
    )


def load_profile(profile_name: str, expected_runtime: str | None = None) -> tuple[Path, dict[str, Any]]:
    ensure_runtime_dirs()
    env = parse_env_file()

    profile_path = resolve_profile_path(profile_name)
    profile_data = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    profile_data = resolve_profile_values(profile_data, env)

    runtime = profile_data.get("runtime")
    if expected_runtime and runtime != expected_runtime:
        raise ValueError(
            f"Profile runtime is '{runtime}', expected '{expected_runtime}'."
        )

    return profile_path, profile_data


def list_profiles(runtime: str | None = None) -> list[Path]:
    ensure_runtime_dirs()
    paths = sorted(get_local_profile_dir().glob("*.y*ml"))

    if runtime is None:
        return paths

    filtered: list[Path] = []
    for path in paths:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue

        if data.get("runtime") == runtime:
            filtered.append(path)

    return filtered


def slugify_profile(profile_name: str) -> str:
    stem = Path(profile_name).stem
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-").lower()
    return slug or "default"


def profile_log_prefix(runtime: str, profile_name: str) -> str:
    return f"{runtime}-{slugify_profile(profile_name)}"


def profile_latest_log_path(runtime: str, profile_name: str) -> Path:
    return get_profile_log_dir() / f"{profile_log_prefix(runtime, profile_name)}-latest.log"


def profile_new_log_path(runtime: str, profile_name: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return get_profile_log_dir() / f"{profile_log_prefix(runtime, profile_name)}-{timestamp}.log"


def state_paths(runtime: str, profile_name: str) -> tuple[Path, Path]:
    ensure_runtime_dirs()
    pid_path = get_pid_dir() / f"{profile_log_prefix(runtime, profile_name)}.pid"
    log_path = profile_latest_log_path(runtime, profile_name)
    return pid_path, log_path


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def format_profile_endpoint(profile: dict[str, Any]) -> str | None:
    server = profile.get("server")
    if not isinstance(server, dict):
        return None

    host = server.get("host")
    port = server.get("port")

    host_str = "" if is_blank(host) else str(host).strip()
    port_str = "" if is_blank(port) else str(port).strip()

    if host_str and port_str:
        return f"{host_str}:{port_str}"
    if host_str:
        return host_str
    if port_str:
        return f":{port_str}"
    return None


def is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def resolve_runtime_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((ROOT_DIR / path).resolve())


def validate_speculative_args(args: dict[str, Any], runtime_name: str) -> None:
    draft_model = args.get("draft-model")
    num_draft_tokens = args.get("num-draft-tokens")

    if is_blank(draft_model) and not is_blank(num_draft_tokens):
        raise ValueError(
            f"{runtime_name} profile sets num-draft-tokens without draft-model."
        )

    if is_blank(num_draft_tokens):
        return

    try:
        parsed = int(str(num_draft_tokens))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{runtime_name} profile num-draft-tokens must be an integer."
        ) from exc

    if parsed <= 0:
        raise ValueError(
            f"{runtime_name} profile num-draft-tokens must be greater than zero."
        )


def validate_mlx_module(module_name: str) -> None:
    allowed_modules = {"mlx_vlm.server", "mlx_lm.server"}
    if module_name not in allowed_modules:
        raise ValueError(
            "mlx profile module must be one of: mlx_vlm.server, mlx_lm.server."
        )


def _normalize_hf_cache_repo_dir(model_ref: str) -> str:
    ref = model_ref.strip().strip("/")
    if ref.startswith("models--"):
        return ref

    if "/" in ref:
        return "models--" + ref.replace("/", "--")

    return "models--" + ref


def _pick_latest_snapshot(snapshots_dir: Path) -> Path:
    candidates = [p for p in snapshots_dir.iterdir() if p.is_dir()]
    if not candidates:
        raise FileNotFoundError(
            f"No snapshots found in {snapshots_dir}. "
            "Download the model first with `hf download <repo_id>`."
        )

    return max(candidates, key=lambda p: p.stat().st_mtime)


def resolve_model_reference(value: str) -> str:
    model_ref = value.strip()
    if not model_ref:
        return model_ref

    expanded = Path(model_ref).expanduser()
    if expanded.is_absolute():
        return str(expanded)

    local_candidate = (ROOT_DIR / expanded).resolve()
    if expanded.exists() or local_candidate.exists():
        return str(local_candidate)

    repo_dir = _normalize_hf_cache_repo_dir(model_ref)
    snapshots_dir = HF_CACHE_ROOT / repo_dir / "snapshots"
    if not snapshots_dir.exists():
        raise FileNotFoundError(
            f"Model reference '{model_ref}' is not absolute and no local cache snapshots were found at {snapshots_dir}. "
            "Download the model first with `hf download <repo_id>`."
        )

    snapshot = _pick_latest_snapshot(snapshots_dir)
    return str(snapshot.resolve())


def resolve_model_args(args: dict[str, Any], runtime_name: str) -> dict[str, Any]:
    resolved = dict(args)
    for key in ("model", "draft-model"):
        value = resolved.get(key)
        if is_blank(value):
            continue

        try:
            resolved[key] = resolve_model_reference(str(value))
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"{runtime_name} profile could not resolve '{key}': {exc}"
            ) from exc

    return resolved

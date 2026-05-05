from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
LOCAL_PROFILE_DIR = ROOT_DIR / "storage" / "project-local-config" / "profiles" / "models"
EXAMPLE_PROFILE_DIR = ROOT_DIR / "project-config" / "models"
PID_DIR = ROOT_DIR / "storage" / "project-local-config" / "pids"
ENV_FILE = ROOT_DIR / ".env"


def ensure_runtime_dirs() -> None:
    LOCAL_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    EXAMPLE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)


def parse_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    if not path.exists():
        return {}

    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()

    return env


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

    if candidate.is_absolute():
        candidates.append(candidate)
    else:
        candidates.append(LOCAL_PROFILE_DIR / candidate)
        if candidate.suffix not in {".yaml", ".yml"}:
            candidates.append(LOCAL_PROFILE_DIR / f"{profile_name}.yaml")
            candidates.append(LOCAL_PROFILE_DIR / f"{profile_name}.yml")

    return candidates


def resolve_profile_path(profile_name: str) -> Path:
    for candidate in _candidate_profile_paths(profile_name):
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"Profile '{profile_name}' was not found in {LOCAL_PROFILE_DIR}."
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
    paths = sorted(LOCAL_PROFILE_DIR.glob("*.y*ml"))

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


def state_paths(runtime: str, profile_name: str) -> tuple[Path, Path]:
    ensure_runtime_dirs()
    slug = slugify_profile(profile_name)
    pid_path = PID_DIR / f"{runtime}-{slug}.pid"
    log_path = PID_DIR / f"{runtime}-{slug}.log"
    return pid_path, log_path


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


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

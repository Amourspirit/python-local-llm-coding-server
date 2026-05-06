from __future__ import annotations

import argparse
import sys
from typing import Any

from common_process import (
    is_pid_running,
    prune_profile_logs,
    read_pid,
    remove_pid,
    start_process,
    stop_pid,
    update_latest_log_link,
    write_pid,
)
from common_profile import (
    get_log_rotation_days,
    is_blank,
    is_truthy,
    list_profiles,
    load_profile,
    profile_log_prefix,
    profile_new_log_path,
    resolve_model_args,
    state_paths,
    validate_mlx_module,
    validate_speculative_args,
)

RUNTIME = "mlx_vlm"


def _first_model_value(profile: dict[str, Any]) -> str | None:
    models = profile.get("models")
    if isinstance(models, list) and models:
        first = models[0]
        if isinstance(first, dict):
            model = first.get("model")
            if isinstance(model, str) and model.strip():
                return model
    return None


def build_mlx_command(profile: dict[str, Any]) -> list[str]:
    python_exec = profile.get("pythonExecutable")
    if not isinstance(python_exec, str) or python_exec.strip() in {"", "python"}:
        python_exec = sys.executable

    module = profile.get("module") or "mlx_vlm.server"
    validate_mlx_module(str(module))
    command = [python_exec, "-m", str(module)]

    server = profile.get("server", {})
    if isinstance(server, dict):
        host = server.get("host")
        port = server.get("port")
        if not is_blank(host):
            command.extend(["--host", str(host)])
        if not is_blank(port):
            command.extend(["--port", str(port)])

    args = profile.get("mlxServerArgs", {})
    if not isinstance(args, dict):
        args = {}

    validate_speculative_args(args, "mlx")
    args = resolve_model_args(args, "mlx")

    model = args.get("model") or _first_model_value(profile)
    if is_blank(model):
        raise ValueError("mlx profile is missing mlxServerArgs.model (or models[0].model).")

    if "model" not in args:
        command.extend(["--model", str(model)])

    for raw_key, value in args.items():
        key = str(raw_key).replace("_", "-")
        if key == "model":
            command.extend(["--model", str(value)])
            continue

        if isinstance(value, bool):
            if value:
                command.append(f"--{key}")
            continue

        if is_blank(value):
            continue

        if is_truthy(value) and str(value).strip().lower() in {"true", "false"}:
            if is_truthy(value):
                command.append(f"--{key}")
            continue

        command.extend([f"--{key}", str(value)])

    return command


def cmd_start(profile_name: str) -> int:
    _, profile = load_profile(profile_name, expected_runtime=RUNTIME)
    pid_path, latest_log_path = state_paths(RUNTIME, profile_name)
    rotation_days = get_log_rotation_days()

    existing = read_pid(pid_path)
    if existing and is_pid_running(existing):
        print(f"mlx_vlm profile '{profile_name}' is already running with pid {existing}.")
        return 1

    if existing and not is_pid_running(existing):
        remove_pid(pid_path)

    log_prefix = profile_log_prefix(RUNTIME, profile_name)
    prune_profile_logs(latest_log_path.parent, log_prefix, rotation_days)

    log_path = profile_new_log_path(RUNTIME, profile_name)
    command = build_mlx_command(profile)
    pid = start_process(command, log_path)
    update_latest_log_link(latest_log_path, log_path)
    write_pid(pid_path, pid)

    print(f"started mlx_vlm profile '{profile_name}'")
    print(f"pid: {pid}")
    print(f"log: {log_path}")
    if latest_log_path != log_path:
        print(f"latest log: {latest_log_path}")
    return 0


def cmd_status(profile_name: str) -> int:
    pid_path, latest_log_path = state_paths(RUNTIME, profile_name)
    pid = read_pid(pid_path)

    if not pid:
        print(f"mlx_vlm profile '{profile_name}' is not running.")
        print(f"expected pid file: {pid_path}")
        return 0

    if is_pid_running(pid):
        print(f"mlx_vlm profile '{profile_name}' is running.")
        print(f"pid: {pid}")
        print(f"log: {latest_log_path}")
        return 0

    print(f"mlx_vlm profile '{profile_name}' has a stale pid file ({pid}).")
    print(f"pid file: {pid_path}")
    return 1


def cmd_stop(profile_name: str) -> int:
    pid_path, _ = state_paths(RUNTIME, profile_name)
    pid = read_pid(pid_path)

    if not pid:
        print(f"mlx_vlm profile '{profile_name}' is not running.")
        return 0

    if not is_pid_running(pid):
        remove_pid(pid_path)
        print(f"removed stale pid file for mlx_vlm profile '{profile_name}'.")
        return 0

    stopped = stop_pid(pid)
    if stopped:
        remove_pid(pid_path)
        print(f"stopped mlx_vlm profile '{profile_name}' (pid {pid}).")
        return 0

    print(f"failed to stop mlx_vlm profile '{profile_name}' (pid {pid}).")
    return 1


def cmd_restart(profile_name: str) -> int:
    stop_code = cmd_stop(profile_name)
    if stop_code not in (0,):
        return stop_code
    return cmd_start(profile_name)


def cmd_list() -> int:
    paths = list_profiles(runtime=RUNTIME)
    if not paths:
        print("no mlx_vlm profiles found.")
        return 0

    for path in paths:
        print(path.stem)
    return 0


def cmd_show(profile_name: str) -> int:
    profile_path, _ = load_profile(profile_name, expected_runtime=RUNTIME)
    print(profile_path.read_text(encoding="utf-8"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage mlx_vlm.server profiles")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start")
    start.add_argument("--profile", required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--profile", required=True)

    stop = subparsers.add_parser("stop")
    stop.add_argument("--profile", required=True)

    restart = subparsers.add_parser("restart")
    restart.add_argument("--profile", required=True)

    subparsers.add_parser("list")

    show = subparsers.add_parser("show")
    show.add_argument("--profile", required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "start":
            return cmd_start(args.profile)
        if args.command == "status":
            return cmd_status(args.profile)
        if args.command == "stop":
            return cmd_stop(args.profile)
        if args.command == "restart":
            return cmd_restart(args.profile)
        if args.command == "list":
            return cmd_list()
        if args.command == "show":
            return cmd_show(args.profile)
    except Exception as exc:
        print(f"error: {exc}")
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

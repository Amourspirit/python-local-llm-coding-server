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
    format_profile_endpoint,
    get_log_rotation_days,
    is_blank,
    is_truthy,
    list_profiles,
    load_profile,
    parse_env_file,
    profile_log_prefix,
    profile_new_log_path,
    resolve_model_args,
    resolve_runtime_path,
    state_paths,
    validate_speculative_args,
)

RUNTIME = "swiftlm"


def _first_model_value(profile: dict[str, Any]) -> str | None:
    models = profile.get("models")
    if isinstance(models, list) and models:
        first = models[0]
        if isinstance(first, dict):
            model = first.get("model")
            if isinstance(model, str) and model.strip():
                return model
    return None


def build_swift_command(profile: dict[str, Any]) -> list[str]:
    env = parse_env_file()
    default_binary = env.get("SWIFT_BIN", "").strip() or "storage/runtimes/swiftlm/bin/SwiftLM"
    binary = profile.get("binary") or default_binary
    command = [resolve_runtime_path(str(binary))]

    server = profile.get("server", {})
    if isinstance(server, dict):
        host = server.get("host")
        port = server.get("port")
        if not is_blank(host):
            command.extend(["--host", str(host)])
        if not is_blank(port):
            command.extend(["--port", str(port)])

    args = profile.get("swiftServerArgs", {})
    if not isinstance(args, dict):
        args = {}

    # Keep startup behavior stable even if profiles omit these keys.
    if is_blank(args.get("parallel")):
        args["parallel"] = 1
    if "turbo-kv" not in args:
        args["turbo-kv"] = False

    validate_speculative_args(args, "swiftlm")
    args = resolve_model_args(args, "swiftlm")

    model = args.get("model") or _first_model_value(profile)
    if is_blank(model):
        raise ValueError("swift profile is missing swiftServerArgs.model (or models[0].model).")

    command.extend(["--model", str(model)])

    value_flags = [
        "max-tokens",
        "ctx-size",
        "temp",
        "top-p",
        "top-k",
        "min-p",
        "repeat-penalty",
        "parallel",
        "mem-limit",
        "api-key",
        "gpu-layers",
        "cors",
        "prefill-size",
        "draft-model",
        "num-draft-tokens",
    ]
    bool_flags = [
        "thinking",
        "vision",
        "audio",
        "info",
        "calibrate",
        "stream-experts",
        "ssd-prefetch",
        "turbo-kv",
    ]

    for key in value_flags:
        value = args.get(key)
        if not is_blank(value):
            command.extend([f"--{key}", str(value)])

    for key in bool_flags:
        if is_truthy(args.get(key)):
            command.append(f"--{key}")

    return command


def cmd_start(profile_name: str) -> int:
    _, profile = load_profile(profile_name, expected_runtime=RUNTIME)
    pid_path, latest_log_path = state_paths(RUNTIME, profile_name)
    rotation_days = get_log_rotation_days()

    existing = read_pid(pid_path)
    if existing and is_pid_running(existing):
        print(f"swiftlm profile '{profile_name}' is already running with pid {existing}.")
        return 1

    if existing and not is_pid_running(existing):
        remove_pid(pid_path)

    log_prefix = profile_log_prefix(RUNTIME, profile_name)
    prune_profile_logs(latest_log_path.parent, log_prefix, rotation_days)

    log_path = profile_new_log_path(RUNTIME, profile_name)
    command = build_swift_command(profile)
    pid = start_process(command, log_path)
    update_latest_log_link(latest_log_path, log_path)
    write_pid(pid_path, pid)

    print(f"started swiftlm profile '{profile_name}'")
    print(f"pid: {pid}")
    print(f"log: {log_path}")
    if latest_log_path != log_path:
        print(f"latest log: {latest_log_path}")
    return 0


def cmd_status(profile_name: str) -> int:
    pid_path, latest_log_path = state_paths(RUNTIME, profile_name)
    pid = read_pid(pid_path)
    endpoint = None
    try:
        _, profile = load_profile(profile_name, expected_runtime=RUNTIME)
        endpoint = format_profile_endpoint(profile)
    except Exception:
        endpoint = None

    if not pid:
        print(f"swiftlm profile '{profile_name}' is not running.")
        if endpoint:
            print(f"endpoint: {endpoint}")
        print(f"expected pid file: {pid_path}")
        return 0

    if is_pid_running(pid):
        print(f"swiftlm profile '{profile_name}' is running.")
        if endpoint:
            print(f"endpoint: {endpoint}")
        print(f"pid: {pid}")
        print(f"log: {latest_log_path}")
        return 0

    print(f"swiftlm profile '{profile_name}' has a stale pid file ({pid}).")
    if endpoint:
        print(f"endpoint: {endpoint}")
    print(f"pid file: {pid_path}")
    return 1


def cmd_stop(profile_name: str) -> int:
    pid_path, _ = state_paths(RUNTIME, profile_name)
    pid = read_pid(pid_path)

    if not pid:
        print(f"swiftlm profile '{profile_name}' is not running.")
        return 0

    if not is_pid_running(pid):
        remove_pid(pid_path)
        print(f"removed stale pid file for swiftlm profile '{profile_name}'.")
        return 0

    stopped = stop_pid(pid)
    if stopped:
        remove_pid(pid_path)
        print(f"stopped swiftlm profile '{profile_name}' (pid {pid}).")
        return 0

    print(f"failed to stop swiftlm profile '{profile_name}' (pid {pid}).")
    return 1


def cmd_restart(profile_name: str) -> int:
    stop_code = cmd_stop(profile_name)
    if stop_code not in (0,):
        return stop_code
    return cmd_start(profile_name)


def cmd_list() -> int:
    paths = list_profiles(runtime=RUNTIME)
    if not paths:
        print("no swiftlm profiles found.")
        return 0

    for path in paths:
        print(path.stem)
    return 0


def cmd_show(profile_name: str) -> int:
    profile_path, _ = load_profile(profile_name, expected_runtime=RUNTIME)
    print(profile_path.read_text(encoding="utf-8"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage SwiftLM profiles")
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

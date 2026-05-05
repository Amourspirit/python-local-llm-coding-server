from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path


def read_pid(pid_path: Path) -> int | None:
    if not pid_path.exists():
        return None

    raw = pid_path.read_text(encoding="utf-8").strip()
    if not raw:
        return None

    try:
        return int(raw)
    except ValueError:
        return None


def write_pid(pid_path: Path, pid: int) -> None:
    pid_path.write_text(f"{pid}\n", encoding="utf-8")


def remove_pid(pid_path: Path) -> None:
    if pid_path.exists():
        pid_path.unlink()


def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def start_process(command: list[str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log_file:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return process.pid


def stop_pid(pid: int, timeout_seconds: float = 8.0) -> bool:
    if not is_pid_running(pid):
        return False

    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except PermissionError:
        os.kill(pid, signal.SIGTERM)

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not is_pid_running(pid):
            return True
        time.sleep(0.2)

    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    except PermissionError:
        os.kill(pid, signal.SIGKILL)

    return not is_pid_running(pid)

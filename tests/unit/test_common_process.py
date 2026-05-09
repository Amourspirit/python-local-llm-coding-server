from __future__ import annotations

import time
from pathlib import Path

import pytest

import common_process


@pytest.mark.unit
def test_read_pid_missing_file_returns_none(tmp_path: Path) -> None:
    assert common_process.read_pid(tmp_path / "missing.pid") is None


@pytest.mark.unit
def test_read_pid_invalid_value_returns_none(tmp_path: Path) -> None:
    pid_path = tmp_path / "invalid.pid"
    pid_path.write_text("not-a-pid\n", encoding="utf-8")

    assert common_process.read_pid(pid_path) is None


@pytest.mark.unit
def test_read_pid_valid_value(tmp_path: Path) -> None:
    pid_path = tmp_path / "valid.pid"
    pid_path.write_text("12345\n", encoding="utf-8")

    assert common_process.read_pid(pid_path) == 12345


@pytest.mark.unit
def test_prune_profile_logs_removes_old_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    old_log = log_dir / "swiftlm-demo-20200101.log"
    new_log = log_dir / "swiftlm-demo-20260101.log"
    latest_link_name = log_dir / "swiftlm-demo-latest.log"

    old_log.write_text("old", encoding="utf-8")
    new_log.write_text("new", encoding="utf-8")
    latest_link_name.write_text("latest", encoding="utf-8")

    now = time.time()
    old_time = now - (10 * 24 * 60 * 60)
    new_time = now

    old_log.touch()
    new_log.touch()

    monkeypatch.setattr(common_process.time, "time", lambda: now)
    monkeypatch.setattr(common_process.Path, "stat", Path.stat)

    # Ensure file mtimes match expected age windows.
    import os

    os.utime(old_log, (old_time, old_time))
    os.utime(new_log, (new_time, new_time))

    common_process.prune_profile_logs(log_dir, "swiftlm-demo", rotation_days=5)

    assert not old_log.exists()
    assert new_log.exists()
    assert latest_link_name.exists()


@pytest.mark.unit
def test_update_latest_log_link_creates_symlink(tmp_path: Path) -> None:
    latest_log = tmp_path / "demo-latest.log"
    current_log = tmp_path / "demo-20260101.log"
    current_log.write_text("data", encoding="utf-8")

    common_process.update_latest_log_link(latest_log, current_log)

    if common_process.os.name == "nt":
        assert not latest_log.exists()
    else:
        assert latest_log.is_symlink()
        assert latest_log.resolve() == current_log.resolve()

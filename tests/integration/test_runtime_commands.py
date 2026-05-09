from __future__ import annotations

import importlib
from pathlib import Path

import pytest


RUNTIME_MODULES = [
    ("swiftlm_profile", "swiftlm"),
    ("mlx_profile", "mlx_vlm"),
]


def _set_build_command_stub(monkeypatch: pytest.MonkeyPatch, module: object) -> None:
    if getattr(module, "RUNTIME") == "swiftlm":
        monkeypatch.setattr(module, "build_swift_command", lambda _: ["swift", "run"])
    else:
        monkeypatch.setattr(
            module, "build_mlx_command", lambda _: ["python", "-m", "mlx_lm.server"]
        )


@pytest.mark.integration
@pytest.mark.parametrize("module_name,runtime", RUNTIME_MODULES)
def test_cmd_start_returns_one_when_already_running(
    module_name: str,
    runtime: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = importlib.import_module(module_name)
    pid_path = tmp_path / "state.pid"
    latest_log_path = tmp_path / "latest.log"

    monkeypatch.setattr(
        module,
        "load_profile",
        lambda profile_name, expected_runtime=None: (
            Path("profile.yaml"),
            {"runtime": runtime},
        ),
    )
    monkeypatch.setattr(
        module,
        "state_paths",
        lambda runtime_name, profile_name: (pid_path, latest_log_path),
    )
    monkeypatch.setattr(module, "get_log_rotation_days", lambda: 5)
    monkeypatch.setattr(module, "read_pid", lambda _: 12345)
    monkeypatch.setattr(module, "is_pid_running", lambda _: True)
    monkeypatch.setattr(
        module,
        "start_process",
        lambda *_: (_ for _ in ()).throw(
            AssertionError("start_process should not be called")
        ),
    )

    code = module.cmd_start("demo")

    assert code == 1
    assert "already running" in capsys.readouterr().out


@pytest.mark.integration
@pytest.mark.parametrize("module_name,runtime", RUNTIME_MODULES)
def test_cmd_start_removes_stale_pid_and_starts(
    module_name: str,
    runtime: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = importlib.import_module(module_name)
    pid_path = tmp_path / "state.pid"
    latest_log_path = tmp_path / "latest.log"
    current_log_path = tmp_path / "current.log"

    removed: list[Path] = []
    wrote: list[tuple[Path, int]] = []
    updated_links: list[tuple[Path, Path]] = []

    monkeypatch.setattr(
        module,
        "load_profile",
        lambda profile_name, expected_runtime=None: (
            Path("profile.yaml"),
            {"runtime": runtime},
        ),
    )
    monkeypatch.setattr(
        module,
        "state_paths",
        lambda runtime_name, profile_name: (pid_path, latest_log_path),
    )
    monkeypatch.setattr(module, "get_log_rotation_days", lambda: 5)
    monkeypatch.setattr(module, "read_pid", lambda _: 789)
    monkeypatch.setattr(module, "is_pid_running", lambda _: False)
    monkeypatch.setattr(module, "remove_pid", lambda p: removed.append(p))
    monkeypatch.setattr(module, "profile_log_prefix", lambda *_: "prefix")
    monkeypatch.setattr(module, "prune_profile_logs", lambda *_: None)
    monkeypatch.setattr(module, "profile_new_log_path", lambda *_: current_log_path)
    _set_build_command_stub(monkeypatch, module)
    monkeypatch.setattr(module, "start_process", lambda command, log_path: 4321)
    monkeypatch.setattr(
        module,
        "update_latest_log_link",
        lambda latest, current: updated_links.append((latest, current)),
    )
    monkeypatch.setattr(
        module, "write_pid", lambda path, pid: wrote.append((path, pid))
    )

    code = module.cmd_start("demo")

    assert code == 0
    assert removed == [pid_path]
    assert wrote == [(pid_path, 4321)]
    assert updated_links == [(latest_log_path, current_log_path)]
    assert "started" in capsys.readouterr().out


@pytest.mark.integration
@pytest.mark.parametrize("module_name,runtime", RUNTIME_MODULES)
def test_cmd_status_not_running_prints_endpoint(
    module_name: str,
    runtime: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = importlib.import_module(module_name)
    pid_path = tmp_path / "state.pid"
    latest_log_path = tmp_path / "latest.log"

    monkeypatch.setattr(
        module,
        "state_paths",
        lambda runtime_name, profile_name: (pid_path, latest_log_path),
    )
    monkeypatch.setattr(module, "read_pid", lambda _: None)
    monkeypatch.setattr(
        module,
        "load_profile",
        lambda profile_name, expected_runtime=None: (
            Path("profile.yaml"),
            {"runtime": runtime, "server": {"host": "127.0.0.1", "port": 9000}},
        ),
    )
    monkeypatch.setattr(
        module, "format_profile_endpoint", lambda profile: "127.0.0.1:9000"
    )

    code = module.cmd_status("demo")

    out = capsys.readouterr().out
    assert code == 0
    assert "is not running" in out
    assert "endpoint: 127.0.0.1:9000" in out


@pytest.mark.integration
@pytest.mark.parametrize("module_name", ["swiftlm_profile", "mlx_profile"])
def test_cmd_stop_handles_no_pid(
    module_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = importlib.import_module(module_name)
    monkeypatch.setattr(
        module,
        "state_paths",
        lambda runtime_name, profile_name: (
            tmp_path / "state.pid",
            tmp_path / "latest.log",
        ),
    )
    monkeypatch.setattr(module, "read_pid", lambda _: None)

    code = module.cmd_stop("demo")

    assert code == 0
    assert "is not running" in capsys.readouterr().out


@pytest.mark.integration
@pytest.mark.parametrize("module_name", ["swiftlm_profile", "mlx_profile"])
def test_cmd_stop_removes_stale_pid(
    module_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = importlib.import_module(module_name)
    pid_path = tmp_path / "state.pid"
    removed: list[Path] = []

    monkeypatch.setattr(
        module,
        "state_paths",
        lambda runtime_name, profile_name: (pid_path, tmp_path / "latest.log"),
    )
    monkeypatch.setattr(module, "read_pid", lambda _: 321)
    monkeypatch.setattr(module, "is_pid_running", lambda _: False)
    monkeypatch.setattr(module, "remove_pid", lambda p: removed.append(p))

    code = module.cmd_stop("demo")

    assert code == 0
    assert removed == [pid_path]
    assert "removed stale pid file" in capsys.readouterr().out


@pytest.mark.integration
@pytest.mark.parametrize("module_name", ["swiftlm_profile", "mlx_profile"])
def test_cmd_stop_running_process_stops_and_removes_pid(
    module_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = importlib.import_module(module_name)
    pid_path = tmp_path / "state.pid"
    removed: list[Path] = []

    monkeypatch.setattr(
        module,
        "state_paths",
        lambda runtime_name, profile_name: (pid_path, tmp_path / "latest.log"),
    )
    monkeypatch.setattr(module, "read_pid", lambda _: 654)
    monkeypatch.setattr(module, "is_pid_running", lambda _: True)
    monkeypatch.setattr(module, "stop_pid", lambda _: True)
    monkeypatch.setattr(module, "remove_pid", lambda p: removed.append(p))

    code = module.cmd_stop("demo")

    assert code == 0
    assert removed == [pid_path]
    assert "stopped" in capsys.readouterr().out


@pytest.mark.integration
@pytest.mark.parametrize("module_name", ["swiftlm_profile", "mlx_profile"])
def test_cmd_restart_returns_stop_code_without_start_on_stop_failure(
    module_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module(module_name)
    calls: list[str] = []

    def _stop(profile_name: str) -> int:
        calls.append(f"stop:{profile_name}")
        return 1

    def _start(profile_name: str) -> int:
        calls.append(f"start:{profile_name}")
        return 0

    monkeypatch.setattr(module, "cmd_stop", _stop)
    monkeypatch.setattr(module, "cmd_start", _start)

    code = module.cmd_restart("demo")

    assert code == 1
    assert calls == ["stop:demo"]


@pytest.mark.integration
@pytest.mark.parametrize("module_name", ["swiftlm_profile", "mlx_profile"])
def test_cmd_restart_calls_start_after_successful_stop(
    module_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module(module_name)
    calls: list[str] = []

    def _stop(profile_name: str) -> int:
        calls.append(f"stop:{profile_name}")
        return 0

    def _start(profile_name: str) -> int:
        calls.append(f"start:{profile_name}")
        return 7

    monkeypatch.setattr(module, "cmd_stop", _stop)
    monkeypatch.setattr(module, "cmd_start", _start)

    code = module.cmd_restart("demo")

    assert code == 7
    assert calls == ["stop:demo", "start:demo"]

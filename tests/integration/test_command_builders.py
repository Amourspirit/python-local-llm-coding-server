from __future__ import annotations

import pytest

import mlx_profile
import swiftlm_profile


@pytest.mark.integration
def test_build_swift_command_adds_defaults_and_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = {
        "runtime": "swiftlm",
        "server": {"host": "127.0.0.1", "port": 5050},
        "swiftServerArgs": {"model": "mlx-community/gemma-4-31b-it-8bit"},
    }

    monkeypatch.setattr(swiftlm_profile, "parse_env_file", lambda: {})
    monkeypatch.setattr(
        swiftlm_profile, "resolve_runtime_path", lambda _: "/tmp/SwiftLM"
    )
    monkeypatch.setattr(swiftlm_profile, "resolve_model_args", lambda args, _: args)

    command = swiftlm_profile.build_swift_command(profile)

    assert command[0] == "/tmp/SwiftLM"
    assert "--model" in command
    assert "mlx-community/gemma-4-31b-it-8bit" in command
    assert "--parallel" in command
    assert "1" in command
    assert "--turbo-kv" not in command


@pytest.mark.integration
def test_build_mlx_command_maps_args(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = {
        "runtime": "mlx_vlm",
        "module": "mlx_lm.server",
        "server": {"host": "127.0.0.1", "port": 8080},
        "mlxServerArgs": {
            "model": "mlx-community/gemma-4-31b-it-8bit",
            "draft-model": "mlx-community/gemma-4-3b-it-8bit",
            "num-draft-tokens": 8,
            "trust-remote-code": True,
        },
    }

    monkeypatch.setattr(mlx_profile, "resolve_model_args", lambda args, _: args)

    command = mlx_profile.build_mlx_command(profile)

    assert "--model" in command
    assert "mlx-community/gemma-4-31b-it-8bit" in command
    assert "--draft-model" in command
    assert "--num-draft-tokens" in command
    assert "8" in command
    assert "--trust-remote-code" in command


@pytest.mark.integration
def test_build_swift_command_missing_model_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = {
        "runtime": "swiftlm",
        "server": {"host": "127.0.0.1", "port": 5050},
        "swiftServerArgs": {},
    }

    monkeypatch.setattr(swiftlm_profile, "parse_env_file", lambda: {})
    monkeypatch.setattr(
        swiftlm_profile, "resolve_runtime_path", lambda _: "/tmp/SwiftLM"
    )
    monkeypatch.setattr(swiftlm_profile, "resolve_model_args", lambda args, _: args)

    with pytest.raises(ValueError, match="swift profile is missing"):
        swiftlm_profile.build_swift_command(profile)


@pytest.mark.integration
def test_build_mlx_command_missing_model_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = {
        "runtime": "mlx_vlm",
        "module": "mlx_lm.server",
        "server": {"host": "127.0.0.1", "port": 8080},
        "mlxServerArgs": {},
    }

    monkeypatch.setattr(mlx_profile, "resolve_model_args", lambda args, _: args)

    with pytest.raises(ValueError, match="mlx profile is missing"):
        mlx_profile.build_mlx_command(profile)

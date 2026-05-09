# Coding Server

Coding Server manages local model-serving profiles for two backends:

- `swiftlm` via the SwiftLM binary
- `mlx_vlm` via `python -m mlx_vlm.server`

The repo is organized around YAML profile files, background process management, PID tracking, and rotating log files. The main user interface is the `Makefile`; the Python scripts under `scripts/` implement the runtime-specific behavior.

## What This Repo Does

Use this project when you want a repeatable way to:

- keep model server settings in versionable YAML files
- start, stop, restart, and inspect local model servers
- switch between SwiftLM and MLX-VLM profiles with a common workflow
- run a paired main profile and draft profile for local development

This repo is not currently exposed through `main.py`. The supported workflows are the `make` targets and the runtime management scripts in `scripts/`.

## Requirements

- Python 3.9+
- a virtual environment for the project
- model weights already available locally or downloaded through the Hugging Face cache
- for SwiftLM profiles: a working SwiftLM binary, defaulting to `storage/runtimes/swiftlm/bin/SwiftLM`
- for MLX profiles: Python dependencies installed in the environment used to launch `mlx_vlm.server`

## Setup

Sync the project environment with `uv`:

```bash
uv sync
```

If you want an interactive shell inside the synced environment, use:

```bash
source .venv/bin/activate
```

Create a local environment file from the example and adjust the values for your machine:

```bash
cp .env.example .env
```

The `Makefile` reads `.env` immediately and requires both `MODEL_MAIN_PROFILE` and `MODEL_DRAFT_PROFILE` to be set for any `make` command. If you only want to operate on a single profile without setting those variables, run the Python scripts directly instead of `make`.

## Repository Layout

- `project-config/models/`: example profile YAML files you can copy from
- `storage/project-local-config/profiles/models/`: active local profiles used by the scripts
- `storage/project-local-config/pids/`: PID files for running profile processes
- `storage/logs/profiles/`: timestamped logs plus a `-latest.log` symlink per profile
- `scripts/common_profile.py`: profile loading, `.env` parsing, path helpers, and model resolution
- `scripts/common_process.py`: process start/stop helpers and log rotation
- `scripts/swiftlm_profile.py`: SwiftLM profile manager
- `scripts/mlx_profile.py`: MLX profile manager

## Environment Variables

The example file is `.env.example`:

```dotenv
HF_TOKEN=some_token_value
SWIFT_BIN=storage/runtimes/swiftlm/bin/SwiftLM
MODEL_MAIN_PROFILE=swiftlm-Qwen3.5-35B-A3B-8bit
MODEL_DRAFT_PROFILE=swiftlm-AC-Qwen3.5-2B-8bit
LOG_ROTATION_DAYS=5
LOG_PROFILE_PATH=storage/logs/profiles
STORAGE_PATH=storage
```

Notes:

- `SWIFT_BIN` sets the default SwiftLM executable when a SwiftLM profile does not override `binary`.
- `MODEL_MAIN_PROFILE` and `MODEL_DRAFT_PROFILE` are used by `make dev-*` and are also required by the current `Makefile` for all `make` invocations.
- `LOG_ROTATION_DAYS` controls deletion of old timestamped logs. Set it to `0` or a negative value to keep logs forever.
- `STORAGE_PATH` can be relative to the repo root or absolute.
- `HF_TOKEN` is not consumed directly by the scripts, but is useful when your model download tooling needs authenticated Hugging Face access.

## Quick Start

1. Copy one of the example profiles from `project-config/models/` into `storage/project-local-config/profiles/models/`.
2. Update the model reference, host, port, and runtime-specific options.
3. Set `.env` values, especially `MODEL_MAIN_PROFILE` and `MODEL_DRAFT_PROFILE`.
4. List available profiles.
5. Start a profile and verify status.

Example:

```bash
cp project-config/models/example-swiftlm-gemma31b.yaml \
	storage/project-local-config/profiles/models/swiftlm-gemma31b.yaml

make swift-list
make swift-start PROFILE=swiftlm-gemma31b
make swift-status PROFILE=swiftlm-gemma31b
make swift-stop PROFILE=swiftlm-gemma31b
```

## Commands

Show the built-in help:

```bash
make help
```

SwiftLM profile commands:

```bash
make swift-list
make swift-show PROFILE=<profile_name>
make swift-start PROFILE=<profile_name>
make swift-status PROFILE=<profile_name>
make swift-stop PROFILE=<profile_name>
make swift-restart PROFILE=<profile_name>
```

MLX profile commands:

```bash
make mlx-list
make mlx-show PROFILE=<profile_name>
make mlx-start PROFILE=<profile_name>
make mlx-status PROFILE=<profile_name>
make mlx-stop PROFILE=<profile_name>
make mlx-restart PROFILE=<profile_name>
```

Dual-profile development commands:

```bash
make dev-status
make dev-start
make dev-stop
make dev-restart
```

`make dev-start` starts `MODEL_MAIN_PROFILE`, waits five seconds, then starts `MODEL_DRAFT_PROFILE`. `make dev-stop` stops the draft profile first, then the main profile.

## Testing

The project uses `pytest` for unit and integration coverage.

Run all tests:

```bash
make test
```

Run only unit tests:

```bash
make test-unit
```

Run only integration tests:

```bash
make test-integration
```

Pytest discovery and defaults are configured in `pyproject.toml`.

## Direct Script Usage

The `make` targets call the runtime scripts directly. You can use the scripts when you want to avoid `Makefile` constraints or integrate the behavior elsewhere:

```bash
uv run python scripts/swiftlm_profile.py list
uv run python scripts/swiftlm_profile.py start --profile <profile_name>
uv run python scripts/mlx_profile.py list
uv run python scripts/mlx_profile.py start --profile <profile_name>
```

Supported subcommands for both runtimes are `list`, `show`, `start`, `status`, `stop`, and `restart`.

## Profile Files

Profiles are loaded from `storage/project-local-config/profiles/models/`. The repo also includes examples in `project-config/models/`.

Each profile declares its runtime and server settings, then uses runtime-specific argument blocks.

### SwiftLM Example

```yaml
runtime: swiftlm
title: "Gemma 4 31B (SwiftLM)"
provider: "openai"
binary: "storage/runtimes/swiftlm/bin/SwiftLM"
server:
	host: "127.0.0.1"
	port: 5423

swiftServerArgs:
	model: "mlx-community/gemma-4-31b-it-8bit"
	max-tokens: 2048
	temp: 0.7
	repeat-penalty: 1.0
	parallel: 1
	gpu-layers: "auto"
	prefill-size: 512
	draft-model: ""
	num-draft-tokens: ""
	turbo-kv: false
	thinking: false
	vision: false
	audio: false
```

### MLX Example

```yaml
runtime: mlx_vlm
title: "Gemma 4 31B (mlx_vlm.server)"
provider: "openai"
pythonExecutable: "python"
module: "mlx_vlm.server"
server:
	host: "127.0.0.1"
	port: 8066

mlxServerArgs:
	model: "mlx-community/gemma-4-31b-it-8bit"
	draft-model: ""
	num-draft-tokens: ""
	kv-bits: 3.5
	kv-quant-scheme: "turboquant"
	trust-remote-code: false
	log-level: "INFO"
```

### Profile Rules

- `runtime` must match the script used to launch the profile.
- SwiftLM profiles use `swiftServerArgs` and may override `binary`.
- MLX profiles use `mlxServerArgs`, may override `pythonExecutable`, and must use one of these modules: `mlx_vlm.server` or `mlx_lm.server`.
- `draft-model` and `num-draft-tokens` must be configured together when speculative decoding is enabled.
- If the runtime-specific `model` field is omitted, the scripts also check `models[0].model`.
- `${ENV_VAR}` placeholders inside profile YAML are expanded from `.env`.

## Model Resolution

Model references in `model` and `draft-model` are resolved in this order:

1. absolute path
2. path relative to the repository root
3. Hugging Face cache snapshot under `~/.cache/huggingface/hub/`

If you use a Hugging Face repo ID such as `mlx-community/gemma-4-31b-it-8bit`, the scripts expect the model to already exist in the local Hugging Face cache. If no cache snapshot exists, startup fails with guidance to download the model first.

## Logs and Process State

When a profile starts, the scripts:

- write a PID file to `storage/project-local-config/pids/`
- create a timestamped log in `storage/logs/profiles/`
- update a `-latest.log` symlink for the profile on non-Windows systems
- prune older log files according to `LOG_ROTATION_DAYS`

Log and PID filenames are prefixed with the runtime and a slugified profile name, for example `swiftlm-gemma31b`.

## Current Examples in This Repo

The repository includes example profiles for both runtimes and several active local profiles under `storage/project-local-config/profiles/models/`, including:

- SwiftLM Gemma and Qwen variants
- SwiftLM draft-style profiles for paired development setups
- MLX Gemma examples

Those files are the best source of truth for real argument combinations already used with this project.


## Developers notes

When testing Speculative (Draft) models on Mac Os I did not have any luck getting it to work.
There were numerious issues that kept showing up in VS Code (Continue extension) as showing gibberish in the output.
AI said this is a common issue on Mac Os using MLX models from 2026.

My recommendation is don't get lost in trying to get it working.
Use only single model and ommit `draft-model` and `num-draft-tokens` in profiles if having issues.
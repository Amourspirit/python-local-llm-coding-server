from __future__ import annotations

from pathlib import Path

import pytest

import common_profile


@pytest.mark.unit
@pytest.mark.parametrize(
    "value,expected",
    [
        ("mlx-community/gemma-4-31b-it-8bit", True),
        ("org.name/model_name", True),
        ("no-slash", False),
        ("/absolute/path", False),
        ("a//b", False),
    ],
)
def test_is_hf_model_id(value: str, expected: bool) -> None:
    assert common_profile._is_hf_model_id(value) is expected


@pytest.mark.unit
def test_validate_speculative_args_accepts_valid_values() -> None:
    common_profile.validate_speculative_args(
        {"draft-model": "org/draft", "num-draft-tokens": "8"}, "swiftlm"
    )


@pytest.mark.unit
def test_validate_speculative_args_requires_draft_model() -> None:
    with pytest.raises(ValueError, match="num-draft-tokens without draft-model"):
        common_profile.validate_speculative_args(
            {"draft-model": "", "num-draft-tokens": "8"}, "swiftlm"
        )


@pytest.mark.unit
def test_resolve_model_reference_absolute_path_exists(tmp_path: Path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()

    resolved = common_profile.resolve_model_reference(str(model_dir))

    assert resolved == str(model_dir)


@pytest.mark.unit
def test_resolve_model_reference_absolute_path_missing() -> None:
    with pytest.raises(FileNotFoundError, match="Absolute model path"):
        common_profile.resolve_model_reference("/tmp/path-that-should-not-exist-xyz")


@pytest.mark.unit
def test_resolve_model_reference_relative_path_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model_dir = tmp_path / "models" / "local-model"
    model_dir.mkdir(parents=True)
    monkeypatch.setattr(common_profile, "ROOT_DIR", tmp_path)

    resolved = common_profile.resolve_model_reference("models/local-model")

    assert resolved == str(model_dir.resolve())


@pytest.mark.unit
def test_resolve_model_reference_hf_id_cached() -> None:
    common_profile._HF_CACHE_REPO_IDS = {"mlx-community/gemma-4-31b-it-8bit"}

    resolved = common_profile.resolve_model_reference(
        "mlx-community/gemma-4-31b-it-8bit"
    )

    assert resolved == "mlx-community/gemma-4-31b-it-8bit"


@pytest.mark.unit
def test_resolve_model_reference_hf_id_not_cached() -> None:
    common_profile._HF_CACHE_REPO_IDS = set()

    with pytest.raises(FileNotFoundError, match="not present in the local cache"):
        common_profile.resolve_model_reference("mlx-community/gemma-4-31b-it-8bit")


@pytest.mark.unit
def test_resolve_model_reference_relative_path_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(common_profile, "ROOT_DIR", tmp_path)

    with pytest.raises(FileNotFoundError, match="Relative model path"):
        common_profile.resolve_model_reference("missing-local-model")


@pytest.mark.unit
def test_resolve_model_args_wraps_missing_resolution_error() -> None:
    common_profile._HF_CACHE_REPO_IDS = set()

    with pytest.raises(
        FileNotFoundError, match="swiftlm profile could not resolve 'model':"
    ):
        common_profile.resolve_model_args(
            {"model": "mlx-community/gemma-4-31b-it-8bit"}, "swiftlm"
        )

#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import os
from pathlib import Path
import subprocess  # nosec
import time

from provide.testkit.mocking import MagicMock, patch
import pytest

from tofusoup.harness.logic import HarnessBuildError, ensure_go_harness_build


def test_ensure_go_harness_build_success(tmp_path: Path) -> None:
    """Verify that the correct 'go build' command is constructed and run."""
    project_root = tmp_path
    harness_name = "soup-go"

    # Create dummy source directory
    source_dir = project_root / "src/tofusoup/harness/go/soup-go"
    source_dir.mkdir(parents=True)

    # Mock cache directory to use tmp_path instead of real cache
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    with (
        patch("tofusoup.harness.logic.get_cache_dir", return_value=cache_dir),
        patch("tofusoup.harness.logic.run_command") as mock_run,
    ):
        # Mock 'go build' to succeed
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result_path = ensure_go_harness_build(harness_name, project_root, loaded_config={})

        assert result_path.name == "soup-go"

        # Check that 'go build' was called with the correct arguments
        mock_run.assert_called_once()
        args, _kwargs = mock_run.call_args
        assert args[0][0] == "go"
        assert args[0][1] == "build"
        assert "-o" in args[0]
        assert str(result_path) in args[0]


def test_ensure_go_harness_build_failure(tmp_path: Path) -> None:
    """Verify that a build failure raises HarnessBuildError."""
    project_root = tmp_path
    harness_name = "soup-go"

    source_dir = project_root / "src/tofusoup/harness/go/soup-go"
    source_dir.mkdir(parents=True)

    # Mock cache directory to use tmp_path instead of real cache
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    with (
        patch("tofusoup.harness.logic.get_cache_dir", return_value=cache_dir),
        patch("tofusoup.harness.logic.run_command") as mock_run,
    ):
        # Mock 'go build' to fail
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["go", "build"], stderr="go build failed"
        )

        with pytest.raises(HarnessBuildError, match="Failed to build Go harness 'soup-go'"):
            ensure_go_harness_build(harness_name, project_root, loaded_config={})


def _build_with_cached_binary(tmp_path: Path, binary_mtime: float) -> MagicMock:
    """Run the builder with a cached binary of the given age, and report the mock."""
    project_root = tmp_path
    source_dir = project_root / "src/tofusoup/harness/go/soup-go"
    source_dir.mkdir(parents=True)
    (source_dir / "main.go").write_text("package main\n")

    cache_dir = tmp_path / "cache"
    (cache_dir / "harnesses").mkdir(parents=True)
    binary = cache_dir / "harnesses" / "soup-go"
    binary.write_bytes(b"stale")
    os.utime(binary, (binary_mtime, binary_mtime))

    with (
        patch("tofusoup.harness.logic.get_cache_dir", return_value=cache_dir),
        patch("tofusoup.harness.logic.run_command") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        ensure_go_harness_build("soup-go", project_root, loaded_config={})
    return mock_run


def test_a_binary_older_than_its_sources_is_rebuilt(tmp_path: Path) -> None:
    """The harness is a differential oracle, so a stale binary accuses the code under test.

    Without this, the cached binary answered for sources it predated: commands
    added months later came back as "unknown command" and the comparison run
    reported that as a fault in the implementation being compared.
    """
    mock_run = _build_with_cached_binary(tmp_path, binary_mtime=1.0)

    mock_run.assert_called_once()


def test_a_binary_newer_than_its_sources_is_reused(tmp_path: Path) -> None:
    """The cache still has to be a cache."""
    mock_run = _build_with_cached_binary(tmp_path, binary_mtime=time.time() + 3600)

    mock_run.assert_not_called()


# 🥣🔬🔚

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from pathlib import Path
import subprocess

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


# 🥣🔬🔚

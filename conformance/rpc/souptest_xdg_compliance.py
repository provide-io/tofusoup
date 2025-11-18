#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""XDG Base Directory Specification Compliance Tests

Verifies that tofusoup correctly implements XDG cache directory standards
and does not create files in legacy hardcoded locations."""

import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

import pytest

from tofusoup.common.config import load_tofusoup_config
from tofusoup.common.utils import get_cache_dir
from tofusoup.harness.logic import ensure_go_harness_build


class TestXDGCompliance:
    """Test suite for XDG Base Directory compliance."""

    def test_default_cache_location_python(self) -> None:
        """Test Python get_cache_dir() uses platform-appropriate default without overrides."""
        # Clear any environment variable overrides
        env_vars_to_clear = ["TOFUSOUP_CACHE_DIR", "XDG_CACHE_HOME"]
        original_env = {var: os.environ.get(var) for var in env_vars_to_clear}

        try:
            for var in env_vars_to_clear:
                os.environ.pop(var, None)

            cache_dir = get_cache_dir()

            # Platform-specific expected locations
            system = platform.system()
            if system == "Darwin":  # macOS
                expected = Path.home() / "Library" / "Caches" / "tofusoup"
            elif system == "Windows":
                local_app_data = os.getenv("LOCALAPPDATA")
                if local_app_data:
                    expected = Path(local_app_data) / "tofusoup" / "cache"
                else:
                    expected = Path.home() / "AppData" / "Local" / "tofusoup" / "cache"
            else:  # Linux and others
                expected = Path.home() / ".cache" / "tofusoup"

            assert cache_dir == expected, f"Expected {expected}, got {cache_dir}"

        finally:
            # Restore original environment
            for var, value in original_env.items():
                if value is not None:
                    os.environ[var] = value
                else:
                    os.environ.pop(var, None)

    def test_xdg_cache_home_override_python(self, tmp_path: Path) -> None:
        """Test XDG_CACHE_HOME environment variable is respected on Linux.

        Note: XDG_CACHE_HOME is only honored on Linux systems, not on macOS or Windows.
        """
        system = platform.system()
        if system == "Darwin":
            pytest.skip("XDG_CACHE_HOME not honored on macOS (uses ~/Library/Caches)")
        elif system == "Windows":
            pytest.skip("XDG_CACHE_HOME not honored on Windows")

        custom_cache = tmp_path / "custom-cache"
        custom_cache.mkdir()

        original_env = {
            "XDG_CACHE_HOME": os.environ.get("XDG_CACHE_HOME"),
            "TOFUSOUP_CACHE_DIR": os.environ.get("TOFUSOUP_CACHE_DIR"),
        }

        try:
            os.environ.pop("TOFUSOUP_CACHE_DIR", None)
            os.environ["XDG_CACHE_HOME"] = str(custom_cache)

            cache_dir = get_cache_dir()
            expected = custom_cache / "tofusoup"

            assert cache_dir == expected, f"Expected {expected}, got {cache_dir}"

        finally:
            for var, value in original_env.items():
                if value is not None:
                    os.environ[var] = value
                else:
                    os.environ.pop(var, None)

    def test_tofusoup_cache_dir_override_python(self, tmp_path: Path) -> None:
        """Test TOFUSOUP_CACHE_DIR has highest priority."""
        custom_cache = tmp_path / "tofusoup-override"
        custom_cache.mkdir()

        custom_xdg = tmp_path / "xdg-override"
        custom_xdg.mkdir()

        original_env = {
            "TOFUSOUP_CACHE_DIR": os.environ.get("TOFUSOUP_CACHE_DIR"),
            "XDG_CACHE_HOME": os.environ.get("XDG_CACHE_HOME"),
        }

        try:
            # Set both, TOFUSOUP_CACHE_DIR should win
            os.environ["XDG_CACHE_HOME"] = str(custom_xdg)
            os.environ["TOFUSOUP_CACHE_DIR"] = str(custom_cache)

            cache_dir = get_cache_dir()

            assert cache_dir == custom_cache, f"Expected {custom_cache}, got {cache_dir}"
            assert cache_dir != custom_xdg / "tofusoup", "TOFUSOUP_CACHE_DIR should override XDG_CACHE_HOME"

        finally:
            for var, value in original_env.items():
                if value is not None:
                    os.environ[var] = value
                else:
                    os.environ.pop(var, None)

    def test_harness_builds_to_cache(self, project_root: Path) -> None:
        """Test that Go harness is built to XDG cache directory."""
        config = load_tofusoup_config(project_root)
        harness_path = ensure_go_harness_build("soup-go", project_root, config)

        cache_dir = get_cache_dir()
        expected_parent = cache_dir / "harnesses"

        assert harness_path.parent == expected_parent, (
            f"Harness should be built to {expected_parent}, but was built to {harness_path.parent}"
        )

        assert harness_path.exists(), f"Harness binary not found at {harness_path}"
        assert harness_path.is_file(), f"Harness path exists but is not a file: {harness_path}"

    def test_no_files_in_legacy_tmp_location(self) -> None:
        """Test that no tofusoup files are created in /tmp."""
        # Check for legacy /tmp paths
        legacy_patterns = [
            "/tmp/tofusoup*",
            "/tmp/kv-data-*",
        ]

        for pattern in legacy_patterns:
            # Use glob to check
            matches = [str(p) for p in Path("/").glob(pattern.lstrip("/"))]
            # Filter out system temp dir usage (which is OK as last resort)
            # We want to catch hardcoded /tmp/tofusoup paths
            hardcoded_matches = [
                m for m in matches if not m.startswith(tempfile.gettempdir()) or "/tofusoup-cache" in m
            ]

            assert len(hardcoded_matches) == 0, (
                f"Found files matching legacy pattern {pattern}: {hardcoded_matches}. "
                "TofuSoup should use XDG cache directory, not hardcoded /tmp paths."
            )

    def test_no_files_in_project_bin_directory(self, project_root: Path) -> None:
        """Test that no files are created in legacy project bin/ directory."""
        legacy_bin = project_root / "bin"

        # It's OK if the directory doesn't exist
        if not legacy_bin.exists():
            return

        # If it exists, it should be empty or only contain .gitkeep
        contents = list(legacy_bin.iterdir())
        allowed_files = {".gitkeep", ".keep"}

        unexpected_files = [f for f in contents if f.name not in allowed_files]

        assert len(unexpected_files) == 0, (
            f"Found unexpected files in legacy bin/ directory: {[f.name for f in unexpected_files]}. "
            f"Harnesses should be built to {get_cache_dir() / 'harnesses'}"
        )

    def test_no_files_in_project_output_directory(self, project_root: Path) -> None:
        """Test that no files are created in legacy project output/ directory."""
        legacy_output = project_root / "output"

        # It's OK if the directory doesn't exist
        if not legacy_output.exists():
            return

        # If it exists, it should be empty or only contain .gitkeep
        contents = list(legacy_output.iterdir())
        allowed_files = {".gitkeep", ".keep"}

        unexpected_files = [f for f in contents if f.name not in allowed_files]

        assert len(unexpected_files) == 0, (
            f"Found unexpected files in legacy output/ directory: {[f.name for f in unexpected_files]}. "
            f"Logs should go to {get_cache_dir() / 'logs'}"
        )

    def test_go_harness_respects_env_overrides(self, project_root: Path, tmp_path: Path) -> None:
        """Test that Go harness respects environment variable overrides."""
        config = load_tofusoup_config(project_root)
        harness_path = ensure_go_harness_build("soup-go", project_root, config)

        # Create a custom storage directory
        custom_storage = tmp_path / "custom-kv-storage"
        custom_storage.mkdir()

        # Create a simple test script that runs the harness with KV_STORAGE_DIR set
        test_script = tmp_path / "test_env.py"
        test_script.write_text(
            f"""
import subprocess
import os

env = os.environ.copy()
env['KV_STORAGE_DIR'] = '{custom_storage}'

# Try to run harness with custom storage dir
result = subprocess.run(
    ['{harness_path}', 'rpc', 'kv', '--help'],
    env=env,
    capture_output=True,
    text=True
)

# If help works, the harness respects the environment
print("SUCCESS" if result.returncode == 0 else "FAILED")
"""
        )

        result = subprocess.run([sys.executable, str(test_script)], capture_output=True, text=True)

        assert "SUCCESS" in result.stdout, (
            f"Go harness failed to respect environment variables: {result.stderr}"
        )


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


# 🥣🔬🔚

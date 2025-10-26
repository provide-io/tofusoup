"""
Go Client → Python Server RPC Conformance Test

Tests Go client connecting to Python server to verify
cross-language RPC compatibility.

Converted from test_go_to_python.py in project root.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.fixture
def soup_go_path() -> Path | None:
    """Find the soup-go executable."""
    candidates = [
        Path("bin/soup-go"),
        Path("harnesses/bin/soup-go"),
        Path(__file__).parent.parent.parent / "bin" / "soup-go",
    ]

    for path in candidates:
        if path.exists():
            return path.resolve()

    soup_go = shutil.which("soup-go")
    if soup_go:
        return Path(soup_go)

    return None


@pytest.fixture
def soup_path() -> Path | None:
    """Find the soup executable (Python)."""
    soup = shutil.which("soup")
    if soup:
        return Path(soup)
    return None


def test_go_client_python_server(soup_go_path: Path | None, soup_path: Path | None) -> None:
    """Test Go client → Python server using soup-go's client test."""
    if soup_go_path is None:
        pytest.skip("soup-go executable not found")
    if soup_path is None:
        pytest.skip("soup executable not found in PATH")

    # The Go client will start the Python server via the soup executable
    # and the soup executable will run `rpc server-start` when invoked by go-plugin
    env = os.environ.copy()
    env["KV_STORAGE_DIR"] = "/tmp"
    env["LOG_LEVEL"] = "INFO"
    env["BASIC_PLUGIN"] = "hello"
    env["PLUGIN_MAGIC_COOKIE_KEY"] = "BASIC_PLUGIN"

    # NOTE: This test calls a non-existent command "soup-go rpc client test"
    # This test should be rewritten or deleted - see test_cross_language_comprehensive.py
    # for the correct implementation of Go client → Python server testing
    result = subprocess.run(
        [str(soup_go_path), "rpc", "client", "test", str(soup_path)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )

    assert result.returncode == 0, f"Go→Python test failed (exit code {result.returncode}): {result.stderr}"

    # Verify successful operations
    assert "Put operation successful" in result.stdout, "Put operation not confirmed in output"
    assert "Get operation successful" in result.stdout, "Get operation not confirmed in output"

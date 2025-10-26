"""
Cross-Language RPC Conformance Tests

Tests all combinations of Go and Python clients/servers to verify
that put/get operations work correctly across language boundaries.

This consolidates and improves upon the original test_cross_language_proof.py
by using proper pytest fixtures and removing hardcoded paths.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import shutil
import subprocess
import time

import pytest


@pytest.fixture
def soup_go_path() -> Path | None:
    """Find the soup-go executable."""
    # Try multiple possible locations
    candidates = [
        Path("bin/soup-go"),
        Path("harnesses/bin/soup-go"),
        Path(__file__).parent.parent.parent / "bin" / "soup-go",
    ]

    for path in candidates:
        if path.exists():
            return path.resolve()

    # Try finding in PATH
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


@pytest.mark.asyncio
async def test_go_to_go(soup_go_path: Path | None) -> None:
    """Test Go client → Go server using built-in test command."""
    if soup_go_path is None:
        pytest.skip("soup-go executable not found")

    env = os.environ.copy()
    env["KV_STORAGE_DIR"] = "/tmp"
    env["LOG_LEVEL"] = "INFO"

    # Run the built-in Go client test
    # This command starts a Go server internally and tests against it
    result = subprocess.run(
        [str(soup_go_path), "rpc", "client", "test", str(soup_go_path)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )

    assert result.returncode == 0, f"Go→Go test failed: {result.stderr}"
    assert "Put operation successful" in result.stdout
    assert "Get operation successful" in result.stdout


@pytest.mark.asyncio
async def test_python_to_python(soup_path: Path | None) -> None:
    """Test Python client → Python server."""
    if soup_path is None:
        pytest.skip("soup executable not found in PATH")

    from tofusoup.rpc.client import KVClient

    client = KVClient(
        server_path=str(soup_path),
        tls_mode="auto",
        tls_key_type="rsa"
    )

    try:
        # Set a generous timeout as Python→Python may have handshake issues
        await asyncio.wait_for(client.start(), timeout=10.0)

        # Test put operation
        test_key = "test-pypy-proof"
        test_value = b"Hello from Python client to Python server!"

        await client.put(test_key, test_value)

        # Test get operation
        retrieved = await client.get(test_key)

        assert retrieved == test_value, f"Value mismatch: expected {test_value!r}, got {retrieved!r}"

    finally:
        try:
            await client.close()
        except Exception:
            pass


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Python client → Go server is not supported (known issue in pyvider-rpcplugin)",
    raises=(ConnectionError, TimeoutError),
    strict=False
)
async def test_python_to_go(soup_go_path: Path | None) -> None:
    """Test Python client → Go server (known to be unsupported)."""
    if soup_go_path is None:
        pytest.skip("soup-go executable not found")

    from tofusoup.rpc.client import KVClient

    # Create client with EC P-256 (works well with Go)
    client = KVClient(
        server_path=str(soup_go_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="P-256"
    )

    try:
        await asyncio.wait_for(client.start(), timeout=15.0)

        # Test put operation
        test_key = "test-pygo-proof"
        test_value = b"Hello from Python client to Go server!"

        await client.put(test_key, test_value)

        # Test get operation
        retrieved = await client.get(test_key)

        assert retrieved == test_value, f"Value mismatch: expected {test_value!r}, got {retrieved!r}"

    finally:
        try:
            await client.close()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_go_to_python(soup_go_path: Path | None, soup_path: Path | None) -> None:
    """Test Go client → Python server."""
    if soup_go_path is None:
        pytest.skip("soup-go executable not found")
    if soup_path is None:
        pytest.skip("soup executable not found in PATH")

    env = os.environ.copy()
    env["KV_STORAGE_DIR"] = "/tmp"
    env["LOG_LEVEL"] = "INFO"

    # The Go client will start the Python server via the soup executable
    result = subprocess.run(
        [str(soup_go_path), "rpc", "client", "test", str(soup_path)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )

    assert result.returncode == 0, f"Go→Python test failed: {result.stderr}"
    assert "Put operation successful" in result.stdout
    assert "Get operation successful" in result.stdout

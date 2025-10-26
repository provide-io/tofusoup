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
    """Test Go client → Go server by explicitly starting server and client."""
    if soup_go_path is None:
        pytest.skip("soup-go executable not found")

    env = os.environ.copy()
    env["KV_STORAGE_DIR"] = "/tmp"
    env["LOG_LEVEL"] = "INFO"

    # 1. Start the Go server
    server_command = [str(soup_go_path), "rpc", "kv", "server", "--tls-mode", "auto", "--tls-curve", "secp256r1"]
    server_process = subprocess.Popen(
        server_command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for the server to start and output its handshake
    handshake_line = ""
    for _ in range(10):  # Try reading for a few seconds
        line = server_process.stdout.readline()
        if "core_version" in line: # Look for the handshake line
            handshake_line = line.strip()
            break
        await asyncio.sleep(0.5)

    assert handshake_line, "Go server did not output handshake line"
    
    # Extract port from handshake line
    parts = handshake_line.split('|')
    assert len(parts) == 6, f"Invalid handshake line format: {handshake_line}"
    address_part = parts[3]
    port = address_part.split(':')[-1]
    
    # 2. Run the Go client to put a value
    put_key = "go-go-key"
    put_value = "Hello from Go client to Go server!"
    put_command = [
        str(soup_go_path), "rpc", "kv", "put",
        f"--address=127.0.0.1:{port}",
        put_key, put_value
    ]
    put_result = subprocess.run(
        put_command,
        env=env,
        capture_output=True,
        text=True,
        timeout=10
    )
    assert put_result.returncode == 0, f"Go client Put failed: {put_result.stderr}"
    assert f"Key {put_key} put successfully." in put_result.stdout

    # 3. Run the Go client to get the value
    get_command = [
        str(soup_go_path), "rpc", "kv", "get",
        f"--address=127.0.0.1:{port}",
        put_key
    ]
    get_result = subprocess.run(
        get_command,
        env=env,
        capture_output=True,
        text=True,
        timeout=10
    )
    assert get_result.returncode == 0, f"Go client Get failed: {get_result.stderr}"
    assert put_value in get_result.stdout

    # Clean up server process
    server_process.terminate()
    server_process.wait(timeout=5)
    assert server_process.returncode is not None, "Go server process did not terminate"


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
async def test_python_to_go(soup_go_path: Path | None) -> None:
    """Test Python client → Go server."""
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

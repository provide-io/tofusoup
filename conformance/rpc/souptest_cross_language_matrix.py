#!/usr/bin/env python3
"""
Cross-language RPC compatibility test matrix.

Tests all working language pair combinations:
- Python → Python (secp256r1, secp384r1)
- Python → Go (various curves)

Note: These tests use KVClient infrastructure to test cross-language compatibility.
"""
from pathlib import Path
import shutil

from provide.foundation import logger
import pytest

from tofusoup.rpc.client import KVClient


@pytest.fixture
def soup_path() -> Path | None:
    """Find the soup executable (Python)."""
    soup = shutil.which("soup")
    if soup:
        return Path(soup)
    return None


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


@pytest.mark.asyncio
@pytest.mark.parametrize("curve", ["secp256r1", "secp384r1"])
async def test_python_to_python_all_curves(soup_path: Path | None, curve: str) -> None:
    """Test Python client → Python server with each supported curve."""
    if soup_path is None:
        pytest.skip("Python server (soup) not found in PATH")

    client = KVClient(
        server_path=str(soup_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve=curve
    )
    client.connection_timeout = 10

    try:
        await client.start()

        # Verify Put/Get operations
        test_key = f"matrix-test-{curve}"
        test_value = f"Matrix test with {curve}".encode()

        await client.put(test_key, test_value)
        result = await client.get(test_key)

        assert result == test_value

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_python_to_go_all_curves(soup_go_path: Path | None) -> None:
    """Test Python client → Go server with supported curves."""
    if soup_go_path is None:
        pytest.skip("Go server (soup-go) not found")

    for curve in ["secp256r1", "secp384r1"]:
        client = KVClient(
            server_path=str(soup_go_path),
            tls_mode="auto",
            tls_key_type="ec",
            tls_curve=curve
        )
        client.connection_timeout = 10

        try:
            await client.start()

            test_key = f"py-go-matrix-{curve}"
            test_value = f"Python→Go with {curve}".encode()

            await client.put(test_key, test_value)
            result = await client.get(test_key)

            assert result == test_value

        finally:
            await client.close()


@pytest.mark.asyncio
async def test_go_to_go_connection(soup_go_path: Path | None, test_artifacts_dir: Path) -> None:
    """Test Go client → Go server by explicitly starting server and client."""
    import subprocess
    import asyncio
    import os
    import time

    if soup_go_path is None:
        pytest.skip("Go binary (soup-go) not found")

    # Create test-specific directory for all artifacts
    test_dir = test_artifacts_dir / "go_to_go_connection"
    test_dir.mkdir(exist_ok=True)

    env = os.environ.copy()
    env["KV_STORAGE_DIR"] = str(test_dir)
    env["LOG_LEVEL"] = "INFO"
    env["BASIC_PLUGIN"] = "hello"
    env["PLUGIN_MAGIC_COOKIE_KEY"] = "BASIC_PLUGIN"

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
    timeout_seconds = 10
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        line = server_process.stdout.readline()
        if line:
            if "core_version" in line:
                handshake_line = line.strip()
                break
        else:
            # If no line, give the server a moment to produce output
            await asyncio.sleep(0.1)
        
        # Check if the process has terminated prematurely
        if server_process.poll() is not None:
            stderr_output = server_process.stderr.read()
            raise AssertionError(f"Server process terminated prematurely. Stderr: {stderr_output}")

    assert handshake_line, "Go server did not output handshake line"

    # Extract port from handshake line
    parts = handshake_line.split('|')
    assert len(parts) == 6, f"Invalid handshake line format: {handshake_line}"
    address_part = parts[3]
    port = address_part.split(':')[-1]

    # 2. Run the Go client to put a value
    # IMPORTANT: Pass the FULL handshake line (including certificate) so Go client can auto-detect TLS curve
    put_key = "go-go-key-matrix"
    put_value = "Hello from Go client to Go server (matrix)!"
    put_command = [
        str(soup_go_path), "rpc", "kv", "put",
        f"--address={handshake_line}",  # Pass full handshake with certificate
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
        f"--address={handshake_line}",  # Pass full handshake with certificate
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


def test_known_unsupported_combinations() -> None:
    """Document known unsupported combinations (don't test them, just document)."""
    unsupported = [
        ("python", "go", "any", "Python→Go client connections not supported (pyvider-rpcplugin bug)"),
        ("python", "python", "secp521r1", "secp521r1 not supported by grpcio"),
    ]

    # Just document these via logger
    for client, server, curve, reason in unsupported:
        logger.info("Unsupported combination", client=client, server=server, curve=curve, reason=reason)


# 🍲🥄🧪🪄

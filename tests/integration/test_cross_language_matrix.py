#!/usr/bin/env python3
"""
Cross-language RPC compatibility test matrix.

Tests all working language pair combinations:
- Python → Python (secp256r1, secp384r1)
- Go → Python (AutoMTLS)

Note: Python → Go is a known bug in pyvider-rpcplugin and is NOT tested here.
"""
from pathlib import Path

import time

from provide.foundation import logger
import pytest

from tofusoup.rpc.client import KVClient

# Test matrix: (client_type, server_path, curve, description)
WORKING_COMBINATIONS = [
    ("python", "/Users/tim/code/gh/provide-io/pyvider/.venv/bin/soup", "secp256r1", "Python→Python with P-256"),
    ("python", "/Users/tim/code/gh/provide-io/pyvider/.venv/bin/soup", "secp384r1", "Python→Python with P-384"),
    # Note: Go client → Python server tested separately in Go code
]


@pytest.mark.asyncio
@pytest.mark.parametrize("client_type,server_path,curve,description", WORKING_COMBINATIONS)
async def test_cross_language_connection(client_type, server_path, curve, description) -> None:
    """Test that a client can connect to a server with specified curve."""
    server = Path(server_path)

    if not server.exists():
        pytest.skip(f"Server not found: {server}")

    # Create client
    client = KVClient(
        server_path=str(server),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve=curve
    )
    client.connection_timeout = 10

    try:
        # Test connection
        await client.start()

        # Test basic operations
        test_key = f"test-{curve}"
        test_value = f"Test value for {description}".encode()

        await client.put(test_key, test_value)
        result = await client.get(test_key)

        assert result == test_value, f"Value mismatch for {description}"

    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("curve", ["secp256r1", "secp384r1"])
async def test_python_to_python_all_curves(curve) -> None:
    """Test Python client → Python server with each supported curve."""
    server_path = Path("/Users/tim/code/gh/provide-io/pyvider/.venv/bin/soup")

    if not server_path.exists():
        pytest.skip(f"Python server not found: {server_path}")

    client = KVClient(
        server_path=str(server_path),
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


@pytest.mark.skipif(
    not Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go").exists(),
    reason="Go binary not found"
)
@pytest.mark.asyncio
async def test_go_to_go_connection() -> None:
    """Test Go client → Go server by explicitly starting server and client."""
    import subprocess
    import asyncio
    import os

    go_binary = Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go")

    env = os.environ.copy()
    env["KV_STORAGE_DIR"] = "/tmp"
    env["LOG_LEVEL"] = "INFO"

    # 1. Start the Go server
    server_command = [str(go_binary), "rpc", "kv", "server", "--tls-mode", "auto", "--tls-curve", "secp256r1"]
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
    put_key = "go-go-key-matrix"
    put_value = "Hello from Go client to Go server (matrix)!"
    put_command = [
        str(go_binary), "rpc", "kv", "put",
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
        str(go_binary), "rpc", "kv", "get",
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

#!/usr/bin/env python3
"""
Cross-language RPC compatibility test matrix.

Tests all working language pair combinations:
- Python → Python (secp256r1, secp384r1)
- Go → Python (AutoMTLS)

Note: Python → Go is a known bug in pyvider-rpcplugin and is NOT tested here.
"""
from pathlib import Path

import pytest
from provide.foundation import logger

from tofusoup.rpc.client import KVClient


# Test matrix: (client_type, server_path, curve, description)
WORKING_COMBINATIONS = [
    ("python", "/Users/tim/code/gh/provide-io/pyvider/.venv/bin/soup", "secp256r1", "Python→Python with P-256"),
    ("python", "/Users/tim/code/gh/provide-io/pyvider/.venv/bin/soup", "secp384r1", "Python→Python with P-384"),
    # Note: Go client → Python server tested separately in Go code
]


@pytest.mark.asyncio
@pytest.mark.parametrize("client_type,server_path,curve,description", WORKING_COMBINATIONS)
async def test_cross_language_connection(client_type, server_path, curve, description):
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
async def test_python_to_python_all_curves(curve):
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
def test_go_to_go_connection():
    """
    Test Go client → Go server.

    This is tested via the Go test harness (soup-go rpc client test soup-go).
    We invoke it here to prove it works.
    """
    import subprocess

    go_binary = Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go")

    # Run Go client connecting to Go server
    result = subprocess.run(
        [str(go_binary), "rpc", "client", "test", str(go_binary)],
        capture_output=True,
        text=True,
        timeout=15
    )

    logger.debug("Go→Go test output", stdout=result.stdout, stderr=result.stderr)

    # Check if test passed
    assert result.returncode == 0, f"Go→Go test failed: {result.stderr}"
    assert "completed successfully" in result.stdout, "Go→Go test did not complete successfully"


def test_known_unsupported_combinations():
    """Document known unsupported combinations (don't test them, just document)."""
    unsupported = [
        ("python", "go", "any", "Python→Go client connections not supported (pyvider-rpcplugin bug)"),
        ("python", "python", "secp521r1", "secp521r1 not supported by grpcio"),
    ]

    # Just document these via logger
    for client, server, curve, reason in unsupported:
        logger.info("Unsupported combination", client=client, server=server, curve=curve, reason=reason)


# 🍲🥄🧪🪄

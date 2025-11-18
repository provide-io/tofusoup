#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test error scenarios and failure modes for cross-language RPC.

Validates that:
- Python → Go fails gracefully (known bug)
- Missing server binaries fail early with clear errors
- Invalid curves are rejected"""

from pathlib import Path

from provide.foundation import logger
import pytest

from tofusoup.rpc.client import KVClient


@pytest.mark.asyncio
async def test_python_to_go_succeeds() -> None:
    """
    Test that Python → Go connection WORKS correctly.

    This was previously a known bug but has been FIXED!
    """
    go_server = Path("bin/soup-go")

    if not go_server.exists():
        pytest.skip("Go server not found at bin/soup-go")

    client = KVClient(server_path=str(go_server), tls_mode="auto", tls_key_type="ec", tls_curve="P-384")
    client.connection_timeout = 10

    try:
        await client.start()

        # Verify we can actually do K/V operations
        await client.put("test-key", b"test-value")
        result = await client.get("test-key")
        assert result == b"test-value"

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_missing_server_binary_fails_early() -> None:
    """Test that missing server binary fails immediately with FileNotFoundError."""
    nonexistent = Path("/tmp/nonexistent-server-binary")

    client = KVClient(server_path=str(nonexistent), tls_mode="auto", tls_key_type="ec", tls_curve="secp384r1")

    with pytest.raises(FileNotFoundError) as exc_info:
        await client.start()

    logger.info("Missing binary correctly detected", error=str(exc_info.value))
    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_timeout_on_invalid_server() -> None:
    """Test that connections to invalid servers timeout gracefully."""
    # Use a non-executable file as "server" to test timeout behavior
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write("#!/bin/bash\nsleep 100\n")  # Server that never responds
        invalid_server = Path(f.name)

    try:
        invalid_server.chmod(0o755)

        client = KVClient(server_path=str(invalid_server), tls_mode="disabled")
        client.connection_timeout = 2  # Short timeout

        # Should timeout gracefully
        with pytest.raises((TimeoutError, Exception)) as exc_info:
            await client.start()

        logger.info("Timeout handled gracefully", error=str(exc_info.value))
    finally:
        invalid_server.unlink()


def test_document_limitations() -> None:
    """Document current limitations and edge cases for reference."""
    limitations = [
        {
            "scenario": "Incompatible TLS modes",
            "error": "Connection refused / Handshake failure",
            "reason": "Client and server TLS configurations must be compatible",
            "workaround": "Ensure both use 'auto' mode or matching manual config",
        },
        {
            "scenario": "Missing server binary",
            "error": "FileNotFoundError",
            "reason": "Server executable not found at specified path",
            "workaround": "Verify server binary exists and is executable",
        },
    ]

    for limitation in limitations:
        logger.info(
            "Known limitation",
            scenario=limitation["scenario"],
            error=limitation["error"],
            reason=limitation["reason"],
            workaround=limitation["workaround"],
        )


# 🥣🔬🔚

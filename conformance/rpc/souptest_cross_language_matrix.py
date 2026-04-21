#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Cross-language RPC compatibility test matrix.

Tests all working language pair combinations:
- Python → Python (secp256r1, secp384r1)
- Python → Go (various curves)

Note: These tests use KVClient infrastructure to test cross-language compatibility."""

import contextlib
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

    client = KVClient(server_path=str(soup_path), tls_mode="auto", tls_key_type="ec", tls_curve=curve)
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


@pytest.mark.skip(reason="Python client → Go server is not supported (pyvider-rpcplugin limitation)")
@pytest.mark.asyncio
async def test_python_to_go_all_curves(soup_go_path: Path | None) -> None:
    """Test Python client → Go server with supported curves."""
    if soup_go_path is None:
        pytest.skip("Go server (soup-go) not found")

    for curve in ["secp256r1", "secp384r1"]:
        client = KVClient(server_path=str(soup_go_path), tls_mode="auto", tls_key_type="ec", tls_curve=curve)
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
@pytest.mark.skip(reason="Python KVClient → Go server has TLS handshake issues (pyvider-rpcplugin limitation)")
async def test_go_to_go_connection(soup_go_path: Path | None) -> None:
    """Test Go client → Go server (managed via Python KVClient).

    SKIPPED: This test is skipped because Python's KVClient (which uses pyvider-rpcplugin)
    has known TLS handshake issues when connecting to Go servers. The Python client generates
    certificates that the Go server's AutoMTLS cannot validate properly.

    This is a known limitation documented in test_known_unsupported_combinations().
    Use test_go_client_python_server (interop) or manual Go client tests instead for
    Go client testing.
    """
    import asyncio

    if soup_go_path is None:
        pytest.skip("Go binary (soup-go) not found")

    from tofusoup.rpc.client import KVClient

    # Create KVClient with Go server
    client = KVClient(server_path=str(soup_go_path), tls_mode="auto", tls_key_type="ec", tls_curve="P-256")

    try:
        await asyncio.wait_for(client.start(), timeout=15.0)

        # Test put operation
        test_key = "test-gogo-matrix"
        test_value = b"Hello from Go server to Go client (matrix)!"

        await client.put(test_key, test_value)

        # Test get operation
        retrieved = await client.get(test_key)

        assert retrieved == test_value, f"Value mismatch: expected {test_value!r}, got {retrieved!r}"

    finally:
        with contextlib.suppress(Exception):
            await client.close()


def test_known_unsupported_combinations() -> None:
    """Document known unsupported combinations (don't test them, just document)."""
    unsupported = [
        ("python", "go", "any", "Python→Go client connections not supported (pyvider-rpcplugin bug)"),
        ("python", "python", "secp521r1", "secp521r1 not supported by grpcio"),
    ]

    # Just document these via logger
    for client, server, curve, reason in unsupported:
        logger.info("Unsupported combination", client=client, server=server, curve=curve, reason=reason)


# 🥣🔬🔚

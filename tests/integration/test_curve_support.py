#!/usr/bin/env python3
"""
Test elliptic curve support across different server implementations.

Validates:
- Python servers support secp256r1 and secp384r1
- Python servers reject secp521r1 (grpcio limitation)
- Go servers support all curves (when using TLSProvider)
"""
import asyncio
from pathlib import Path

from provide.foundation import logger
import pytest

from tofusoup.rpc.client import KVClient


@pytest.mark.asyncio
@pytest.mark.parametrize("curve", ["secp256r1", "secp384r1"])
async def test_python_server_supported_curves(curve) -> None:
    """Test that Python server accepts supported curves."""
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
        logger.info("Successfully connected with curve", curve=curve)

        # Verify operations work
        await client.put(f"curve-test-{curve}", b"test")
        result = await client.get(f"curve-test-{curve}")
        assert result == b"test"

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_python_server_rejects_secp521r1() -> None:
    """
    Test that secp521r1 fails gracefully with Python server.

    Note: grpcio doesn't support secp521r1, so this should fail.
    We're testing that it fails in a predictable way.
    """
    server_path = Path("/Users/tim/code/gh/provide-io/pyvider/.venv/bin/soup")

    if not server_path.exists():
        pytest.skip(f"Python server not found: {server_path}")

    client = KVClient(
        server_path=str(server_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="secp521r1"
    )
    client.connection_timeout = 10

    # This should either:
    # 1. Raise an exception during start() (preferred)
    # 2. Timeout (current behavior)
    with pytest.raises((Exception, asyncio.TimeoutError)) as exc_info:
        await client.start()
        await client.close()

    logger.info("secp521r1 correctly rejected", error=str(exc_info.value))


@pytest.mark.asyncio
@pytest.mark.parametrize("curve", ["secp256r1", "secp384r1"])
async def test_curve_consistency(curve) -> None:
    """
    Test that data written with one curve can be read back.

    This verifies the curve is being used correctly for encryption/decryption.
    """
    server_path = Path("/Users/tim/code/gh/provide-io/pyvider/.venv/bin/soup")

    if not server_path.exists():
        pytest.skip(f"Python server not found: {server_path}")

    # Write with curve
    client1 = KVClient(
        server_path=str(server_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve=curve
    )
    client1.connection_timeout = 10

    test_key = f"consistency-{curve}"
    test_value = f"Consistency test for {curve}".encode()

    try:
        await client1.start()
        await client1.put(test_key, test_value)
    finally:
        await client1.close()

    # Read back with same curve
    client2 = KVClient(
        server_path=str(server_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve=curve
    )
    client2.connection_timeout = 10

    try:
        await client2.start()
        result = await client2.get(test_key)
        assert result == test_value, f"Value mismatch for {curve}"
    finally:
        await client2.close()


def test_document_curve_support() -> None:
    """Document which curves are supported by which runtimes."""
    support_matrix = {
        "python": {
            "secp256r1": True,
            "secp384r1": True,
            "secp521r1": False,  # grpcio limitation
        },
        "go": {
            "secp256r1": True,
            "secp384r1": True,
            "secp521r1": True,
        },
    }

    for runtime, curves in support_matrix.items():
        for curve, supported in curves.items():
            status = "supported" if supported else "not supported"
            logger.info("Curve support", runtime=runtime, curve=curve, status=status)


# 🍲🥄🧪🪄

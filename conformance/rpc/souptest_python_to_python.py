#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Python-to-Python RPC Conformance Tests

Tests Python client → Python server with various TLS configurations
to verify that the pyvider-rpcplugin implementation works correctly.

Consolidates test_python_to_python_pyvider.py, test_py_to_py.py,
and test_py_py_all_curves.py from the project root."""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
import shutil

import pytest


@pytest.fixture
def soup_path() -> Path | None:
    """Find the soup executable (Python)."""
    soup = shutil.which("soup")
    if soup:
        return Path(soup)
    return None


@pytest.mark.asyncio
async def test_python_to_python_rsa(soup_path: Path | None) -> None:
    """Test Python client → Python server with RSA TLS."""
    if soup_path is None:
        pytest.skip("soup executable not found in PATH")

    from tofusoup.rpc.client import KVClient

    client = KVClient(server_path=str(soup_path), tls_mode="auto", tls_key_type="rsa")

    try:
        # Set a generous timeout as Python→Python may have handshake issues
        await asyncio.wait_for(client.start(), timeout=10.0)

        # Test put
        key = "test-py2py-rsa"
        value = b"Hello from Python to Python with RSA!"

        await client.put(key, value)

        # Test get
        result = await client.get(key)

        assert result == value, f"Value mismatch: expected {value!r}, got {result!r}"

    finally:
        with contextlib.suppress(Exception):
            await client.close()


@pytest.mark.parametrize(
    "curve",
    [
        pytest.param("secp256r1", id="P-256 (secp256r1)"),
        pytest.param("secp384r1", id="P-384 (secp384r1)"),
    ],
)
@pytest.mark.asyncio
async def test_python_to_python_ec_curve(soup_path: Path | None, curve: str) -> None:
    """Test Python client → Python server with EC curve."""
    if soup_path is None:
        pytest.skip("soup executable not found in PATH")

    from tofusoup.rpc.client import KVClient

    client = KVClient(server_path=str(soup_path), tls_mode="auto", tls_key_type="ec", tls_curve=curve)

    try:
        await asyncio.wait_for(client.start(), timeout=10.0)

        # Test operations
        test_key = f"test-py2py-{curve}"
        test_value = f"Hello from Python to Python with {curve}!".encode()

        await client.put(test_key, test_value)
        result = await client.get(test_key)

        assert result == test_value, f"Value mismatch for {curve}"

    finally:
        with contextlib.suppress(Exception):
            await client.close()


@pytest.mark.asyncio
async def test_python_to_python_p384(soup_path: Path | None) -> None:
    """Test Python client → Python server with P-384 curve (compatibility test)."""
    if soup_path is None:
        pytest.skip("soup executable not found in PATH")

    from tofusoup.rpc.client import KVClient

    # Use P-384 which matches what pyvider uses by default
    client = KVClient(server_path=str(soup_path), tls_mode="auto", tls_key_type="ec", tls_curve="P-384")

    try:
        await asyncio.wait_for(client.start(), timeout=15.0)

        # Test put
        key = "test-py2py"
        value = b"Hello from Python to Python!"

        await client.put(key, value)

        # Test get
        result = await client.get(key)

        assert result == value

    finally:
        with contextlib.suppress(Exception):
            await client.close()


# 🥣🔬🔚

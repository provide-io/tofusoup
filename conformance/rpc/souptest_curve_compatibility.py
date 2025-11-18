#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Elliptic Curve Compatibility Tests

Tests Python client → Go server with all supported elliptic curves
to verify cross-language TLS compatibility.

Consolidates test_ec_curves.py and test_all_curves.py from the project root."""

from __future__ import annotations

import contextlib
from pathlib import Path
import shutil

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


@pytest.mark.skip(reason="Python client → Go server is not supported (pyvider-rpcplugin limitation)")
@pytest.mark.parametrize(
    "curve",
    [
        pytest.param("P-256", id="P-256 (secp256r1)"),
        pytest.param("P-384", id="P-384 (secp384r1)"),
        pytest.param("P-521", id="P-521 (secp521r1)"),
    ],
)
@pytest.mark.asyncio
async def test_python_to_go_curve(soup_go_path: Path | None, curve: str) -> None:
    """Test Python client → Go server with specific elliptic curve."""
    if soup_go_path is None:
        pytest.skip("soup-go executable not found")

    from tofusoup.rpc.client import KVClient

    client = KVClient(server_path=str(soup_go_path), tls_mode="auto", tls_key_type="ec", tls_curve=curve)

    try:
        await client.start()

        # Test put/get operations
        test_key = f"test-{curve.lower()}"
        test_value = f"Hello from {curve}!".encode()

        await client.put(test_key, test_value)
        result = await client.get(test_key)

        assert result == test_value, f"Value mismatch for {curve}"

    finally:
        with contextlib.suppress(Exception):
            await client.close()


@pytest.mark.skip(reason="Python client → Go server is not supported (pyvider-rpcplugin limitation)")
@pytest.mark.asyncio
async def test_auto_curve(soup_go_path: Path | None) -> None:
    """Test Python client → Go server with auto curve selection (go-plugin default)."""
    if soup_go_path is None:
        pytest.skip("soup-go executable not found")

    from tofusoup.rpc.client import KVClient

    client = KVClient(
        server_path=str(soup_go_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="auto",  # Use go-plugin AutoMTLS default
    )

    try:
        await client.start()

        # Test put/get operations
        test_key = "test-auto-curve"
        test_value = b"Hello from auto curve!"

        await client.put(test_key, test_value)
        result = await client.get(test_key)

        assert result == test_value

    finally:
        with contextlib.suppress(Exception):
            await client.close()


# 🥣🔬🔚

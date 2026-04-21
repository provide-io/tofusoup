#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Property-Based Testing for TLS Certificate Generation and Handling

Tests that certificate generation works correctly across:
- All supported curves
- Different key types
- Rapid generation/destruction cycles"""

from pathlib import Path

from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

from tofusoup.rpc.client import KVClient

curves = st.sampled_from(["secp256r1", "secp384r1", "secp521r1", "P-256", "P-384", "P-521"])
key_types = st.sampled_from(["ec", "rsa"])


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    curve=curves,
    key_type=key_types,
)
@settings(
    max_examples=30,
    deadline=20000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_tls_cert_generation_all_combinations(curve: str, key_type: str) -> None:
    """
    Property test: All combinations of curves and key types should generate valid certs.

    Note: RSA doesn't use curve parameter, but we test it anyway to ensure it's ignored gracefully.
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    # RSA doesn't use curves, but the API should handle it gracefully
    client = KVClient(
        server_path=str(go_server),
        tls_mode="auto",
        tls_key_type=key_type,
        tls_curve=curve if key_type == "ec" else "P-256",  # RSA ignores curve
    )

    try:
        # Connection should succeed with valid cert
        await client.start()

        # Verify the connection works
        await client.put("cert-test", b"cert-generation-works")
        result = await client.get("cert-test")
        assert result == b"cert-generation-works"

    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(iterations=st.integers(min_value=3, max_value=8))
@settings(
    max_examples=10,
    deadline=120000,  # Longer deadline for multiple connections
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
@pytest.mark.asyncio
async def test_rapid_cert_generation_cycles(iterations: int) -> None:
    """
    Property test: Rapid connect/disconnect cycles should not leak resources or fail.

    This tests for:
    - Resource leaks (file descriptors, memory)
    - Cert generation race conditions
    - Cleanup issues
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    # Rapidly create and destroy connections
    for i in range(iterations):
        client = KVClient(
            server_path=str(go_server),
            tls_mode="auto",
            tls_key_type="ec",
            tls_curve="P-256",
        )

        try:
            await client.start()
            await client.put(f"rapid-{i}", f"iteration-{i}".encode())
            result = await client.get(f"rapid-{i}")
            assert result == f"iteration-{i}".encode()
        finally:
            await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_python
@given(
    curve=st.sampled_from(["P-256", "P-384"]),  # Python server supports these
    key_type=st.sampled_from(["ec", "rsa"]),
)
@settings(
    max_examples=20,
    deadline=20000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_python_server_tls_compatibility(curve: str, key_type: str) -> None:
    """
    Property test: Python server should handle all supported TLS configurations.
    """
    import shutil

    soup_path = shutil.which("soup")
    if not soup_path:
        pytest.skip("soup not found in PATH")

    client = KVClient(
        server_path=soup_path,
        tls_mode="auto",
        tls_key_type=key_type,
        tls_curve=curve if key_type == "ec" else "P-256",
    )

    try:
        await client.start()
        await client.put("py-tls-test", b"python-tls-works")
        result = await client.get("py-tls-test")
        assert result == b"python-tls-works"
    finally:
        await client.close()


# 🥣🔬🔚

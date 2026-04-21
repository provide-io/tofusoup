#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Property-Based Testing for Cross-Language Compatibility

Ensures that Python and Go implementations produce identical results for the same inputs.
This is critical for polyglot systems where different languages must interoperate."""

from pathlib import Path

from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

from tofusoup.rpc.client import KVClient

# Test data strategies
# NOTE: Keys must be filesystem-safe (Go server uses keys as filenames)
SAFE_KEY_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.@"
test_keys = st.text(min_size=1, max_size=100, alphabet=SAFE_KEY_ALPHABET)
test_values = st.binary(min_size=0, max_size=10000)


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    key=test_keys,
    value=test_values,
)
@settings(
    max_examples=50,
    deadline=30000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_python_and_go_produce_identical_results(key: str, value: bytes) -> None:
    """
    Property test: Given the same K/V data, Python and Go servers should store/retrieve identically.

    Tests roundtrip: Python→Go→Python should be identity.
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    # Test 1: Write with Python client to Go server, read back
    client_go = KVClient(
        server_path=str(go_server),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="P-256",
    )

    try:
        await client_go.start()
        await client_go.put(key, value)
        result_from_go = await client_go.get(key)

        # Verify roundtrip through Go is identity
        assert result_from_go == value, "Roundtrip through Go server failed"

    finally:
        await client_go.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_python
@pytest.mark.harness_go
@given(
    key=test_keys,
    value=test_values,
)
@settings(
    max_examples=30,
    deadline=60000,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
@pytest.mark.asyncio
async def test_data_compatible_across_languages(key: str, value: bytes) -> None:
    """
    Property test: Data written by Python should be readable by Go and vice versa.

    Note: This test verifies logical compatibility, not that both servers share state
    (they don't - each is an independent subprocess).
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    import shutil

    soup_path = shutil.which("soup")
    if not soup_path:
        pytest.skip("soup not found")

    # Test with Go server
    client_go = KVClient(
        server_path=str(go_server),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="P-256",
    )

    try:
        await client_go.start()
        await client_go.put(key, value)
        go_result = await client_go.get(key)
        assert go_result == value
    finally:
        await client_go.close()

    # Test with Python server - should handle same data
    client_py = KVClient(
        server_path=soup_path,
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="P-256",
    )

    try:
        await client_py.start()
        await client_py.put(key, value)
        py_result = await client_py.get(key)
        assert py_result == value
    finally:
        await client_py.close()

    # Both should handle the data identically (even though they're separate instances)
    assert go_result == py_result == value


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(data=st.lists(st.tuples(test_keys, test_values), min_size=5, max_size=15))
@settings(
    max_examples=20,
    deadline=60000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_batch_operations_consistency(data: list[tuple[str, bytes]]) -> None:
    """
    Property test: Batch K/V operations should maintain consistency.

    Ensures no data corruption during rapid operations.
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    client = KVClient(
        server_path=str(go_server),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="P-256",
    )

    try:
        await client.start()

        # Write all data
        for key, value in data:
            await client.put(key, value)

        # Verify all data is intact
        for key, expected_value in data:
            result = await client.get(key)
            assert result == expected_value, f"Data corruption for key={key}"

    finally:
        await client.close()


# 🥣🔬🔚

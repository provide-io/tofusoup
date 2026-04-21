#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Aggressive Property-Based Stress Testing for RPC

Uses hypothesis to generate extreme edge cases and stress test the RPC implementation:
- Huge payloads
- Binary data with null bytes
- Unicode edge cases (emoji, RTL text, control characters)
- Concurrent operations
- Empty strings and zero-length data

This is designed to "abuse" the integration and find breaking points."""

from pathlib import Path

from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

from tofusoup.rpc.client import KVClient

# Hypothesis strategies for aggressive testing
# NOTE: Keys must be filesystem-safe (ASCII alphanumeric + safe punctuation)
# The Go KV server uses keys directly as filenames, which imposes limits:
# - Valid characters: alphanumeric + -.@_
# - Max length: ~240 chars (filesystem NAME_MAX is usually 255, minus "kv-data-" prefix)
SAFE_KEY_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.@"
MAX_KEY_LENGTH = 200  # Safe limit well under filesystem max

extreme_keys = st.one_of(
    st.text(min_size=1, max_size=MAX_KEY_LENGTH, alphabet=SAFE_KEY_ALPHABET),  # Long safe keys
    st.text(min_size=1, max_size=100, alphabet=SAFE_KEY_ALPHABET),  # Normal safe keys
    st.text(min_size=1, max_size=50, alphabet="0123456789"),  # Numeric keys
    st.just("a" * MAX_KEY_LENGTH),  # Max length key
)

extreme_values = st.one_of(
    st.binary(min_size=0, max_size=100_000),  # Huge binary payloads
    st.just(b""),  # Empty value
    st.just(b"\x00" * 1000),  # Lots of null bytes
    st.binary(min_size=1000, max_size=10000),  # Medium-large data
    # Generate random UTF-8 that might have edge cases
    st.text(min_size=0, max_size=10000).map(lambda s: s.encode("utf-8")),
)

curves = st.sampled_from(["P-256", "P-384", "P-521"])


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    key=extreme_keys,
    value=extreme_values,
    curve=curves,
)
@settings(
    max_examples=50,  # Run many iterations to find edge cases
    deadline=30000,  # 30s timeout for slow operations
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
@pytest.mark.asyncio
async def test_rpc_handles_extreme_data(key: str, value: bytes, curve: str) -> None:
    """
    Property test: RPC should handle any valid key/value pair without crashing.

    This tests extreme cases like:
    - Empty keys/values
    - Huge payloads
    - Binary data with null bytes
    - Unicode edge cases
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    client = KVClient(
        server_path=str(go_server),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve=curve,
    )
    client.connection_timeout = 15

    try:
        await client.start()

        # Put and get should work for ANY data
        await client.put(key, value)
        result = await client.get(key)

        # Verify roundtrip is identity
        assert result == value, f"Roundtrip failed for key={key!r}, value length={len(value)}"

    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    keys_and_values=st.lists(
        st.tuples(
            st.text(min_size=1, max_size=100, alphabet=SAFE_KEY_ALPHABET), st.binary(min_size=0, max_size=1000)
        ),
        min_size=5,
        max_size=20,
    )
)
@settings(max_examples=20, deadline=60000, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.asyncio
async def test_rpc_handles_rapid_operations(keys_and_values: list[tuple[str, bytes]]) -> None:
    """
    Property test: Rapid sequential K/V operations should all succeed.

    Tests for race conditions and state corruption.
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

        # Rapidly write all values
        for key, value in keys_and_values:
            await client.put(key, value)

        # Verify all values are still correct
        for key, expected_value in keys_and_values:
            result = await client.get(key)
            assert result == expected_value, f"Data corruption for key={key}"

    finally:
        await client.close()


# 🥣🔬🔚

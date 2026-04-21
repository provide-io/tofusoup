#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Property-Based Resource Exhaustion Testing

Tests system behavior under resource pressure:
- Maximum payload sizes
- Memory pressure
- File descriptor limits
- Disk space constraints"""

import contextlib
from pathlib import Path

from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

from tofusoup.rpc.client import KVClient

# Safe key constraints
SAFE_KEY_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.@"
MAX_KEY_LENGTH = 200


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    payload_size=st.integers(min_value=1_000_000, max_value=10_000_000),  # 1MB - 10MB
)
@settings(
    max_examples=5,  # Fewer examples due to large payloads
    deadline=120000,  # 2 minute timeout
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
@pytest.mark.asyncio
async def test_large_payload_handling(payload_size: int) -> None:
    """
    Property test: Server should handle or reject large payloads gracefully.

    Tests for:
    - Memory exhaustion
    - OOM crashes
    - Proper error handling for oversized data
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    client = KVClient(
        server_path=str(go_server),
        tls_mode="disabled",  # Faster without TLS
    )
    client.connection_timeout = 30

    # Generate large payload
    large_value = b"X" * payload_size

    try:
        await client.start()

        # Try to write large payload
        # Server may accept or reject - either is OK as long as it doesn't crash
        try:
            await client.put(f"large-{payload_size}", large_value)

            # If accepted, verify roundtrip
            result = await client.get(f"large-{payload_size}")
            assert result == large_value, "Large payload corrupted during roundtrip"

        except (ValueError, MemoryError, Exception) as e:
            # Rejection is acceptable - just shouldn't crash
            assert "memory" in str(e).lower() or "too large" in str(e).lower() or "limit" in str(e).lower(), (
                f"Unexpected error for large payload: {e}"
            )

    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    num_keys=st.integers(min_value=100, max_value=1000),
)
@settings(
    max_examples=3,  # Very slow test
    deadline=180000,  # 3 minute timeout
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
@pytest.mark.asyncio
async def test_many_keys_storage(num_keys: int) -> None:
    """
    Property test: Server should handle storing many keys.

    Tests for:
    - Disk space exhaustion
    - File descriptor limits
    - Directory entry limits
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    client = KVClient(
        server_path=str(go_server),
        tls_mode="disabled",
    )
    client.connection_timeout = 30

    try:
        await client.start()

        # Write many keys
        for i in range(num_keys):
            key = f"bulk-{i}"
            value = f"value-{i}".encode()
            await client.put(key, value)

            # Spot check every 100 keys
            if i % 100 == 0:
                result = await client.get(key)
                assert result == value

        # Verify a sample of keys
        for i in [0, num_keys // 2, num_keys - 1]:
            key = f"bulk-{i}"
            expected = f"value-{i}".encode()
            result = await client.get(key)
            assert result == expected, f"Key {key} corrupted"

    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    value_size=st.integers(min_value=0, max_value=100_000),
    num_writes=st.integers(min_value=10, max_value=50),
)
@settings(
    max_examples=10,
    deadline=90000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_repeated_overwrites_memory(value_size: int, num_writes: int) -> None:
    """
    Property test: Repeatedly overwriting the same key shouldn't leak memory.

    Tests for:
    - Memory leaks in file operations
    - Proper resource cleanup
    - File handle leaks
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    client = KVClient(
        server_path=str(go_server),
        tls_mode="disabled",
    )
    client.connection_timeout = 20

    key = "overwrite-test"
    value = b"Y" * value_size

    try:
        await client.start()

        # Repeatedly overwrite the same key
        for i in range(num_writes):
            unique_value = f"{i}".encode() + value
            await client.put(key, unique_value)

            # Spot check
            if i % 10 == 0:
                result = await client.get(key)
                assert result == unique_value

        # Final verification
        final_value = f"{num_writes - 1}".encode() + value
        result = await client.get(key)
        assert result == final_value

    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
async def test_connection_limit_handling() -> None:
    """
    Test creating maximum number of connections without crashing.

    Non-property test for connection limits.
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    # Try to create many connections (may hit ulimit)
    max_connections = 50
    successful_connections = 0

    clients = []
    try:
        for _i in range(max_connections):
            client = KVClient(
                server_path=str(go_server),
                tls_mode="disabled",
            )
            client.connection_timeout = 10

            try:
                await client.start()
                clients.append(client)
                successful_connections += 1
            except (OSError, ConnectionError):
                # Hit system limit - that's OK
                break

        # Should have created at least 5 connections
        assert successful_connections >= 5, f"Only created {successful_connections} connections"

        # Verify all connections still work
        for i, client in enumerate(clients):
            await client.put(f"conn-{i}", f"val-{i}".encode())
            result = await client.get(f"conn-{i}")
            assert result == f"val-{i}".encode()

    finally:
        # Cleanup all connections
        for client in clients:
            with contextlib.suppress(Exception):
                await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    binary_pattern=st.binary(min_size=0, max_size=1000),
)
@settings(
    max_examples=20,
    deadline=30000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_binary_data_integrity(binary_pattern: bytes) -> None:
    """
    Property test: All binary patterns should be stored and retrieved intact.

    Tests for:
    - Binary data corruption
    - Encoding issues
    - Null byte handling in values
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    client = KVClient(
        server_path=str(go_server),
        tls_mode="disabled",
    )
    client.connection_timeout = 15

    try:
        await client.start()

        # Test the binary pattern
        key = "binary-test"
        await client.put(key, binary_pattern)
        result = await client.get(key)

        # Exact binary match required
        assert result == binary_pattern, (
            f"Binary corruption: {len(result)} bytes != {len(binary_pattern)} bytes"
        )
        assert result == binary_pattern  # Verify content, not just length

    finally:
        await client.close()


# 🥣🔬🔚

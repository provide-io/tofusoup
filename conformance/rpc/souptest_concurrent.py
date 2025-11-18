#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Property-Based Concurrent Connection Testing

Tests multiple simultaneous clients to detect:
- Race conditions across connections
- Connection pool exhaustion
- Concurrent read/write consistency
- Resource leaks under load"""

import asyncio
from pathlib import Path

from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

from tofusoup.rpc.client import KVClient

# Safe key constraints (from property_test_rpc_stress.py)
SAFE_KEY_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.@"
MAX_KEY_LENGTH = 200


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    num_clients=st.integers(min_value=2, max_value=10),
    key=st.text(min_size=1, max_size=100, alphabet=SAFE_KEY_ALPHABET),
    value=st.binary(min_size=0, max_size=1000),
)
@settings(
    max_examples=15,
    deadline=90000,  # 90s for slow concurrent operations
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_concurrent_clients_same_key(num_clients: int, key: str, value: bytes) -> None:
    """
    Property test: Multiple clients writing to the same key should all succeed.

    Tests for:
    - Connection pool limits
    - File locking issues
    - Server crashes under concurrent load
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    clients = []
    try:
        # Create multiple concurrent clients
        for _i in range(num_clients):
            client = KVClient(
                server_path=str(go_server),
                tls_mode="auto",
                tls_key_type="ec",
                tls_curve="P-256",
            )
            client.connection_timeout = 15
            clients.append(client)

        # Start all clients concurrently
        await asyncio.gather(*[client.start() for client in clients])

        # Each client writes the same key with a unique value
        unique_values = [
            f"{value}{i}".encode() if value else f"client-{i}".encode() for i in range(num_clients)
        ]

        # Concurrent writes
        await asyncio.gather(*[clients[i].put(key, unique_values[i]) for i in range(num_clients)])

        # Final value should be one of the written values (we can't predict which due to race)
        final_value = await clients[0].get(key)
        assert final_value in unique_values, f"Got unexpected value: {final_value}"

    finally:
        # Cleanup all clients
        await asyncio.gather(*[client.close() for client in clients], return_exceptions=True)


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    num_concurrent_ops=st.integers(min_value=5, max_value=20),
)
@settings(
    max_examples=10,
    deadline=90000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_concurrent_operations_different_keys(num_concurrent_ops: int) -> None:
    """
    Property test: Concurrent operations on different keys should not interfere.

    Tests for:
    - Isolation between keys
    - No cross-contamination
    - Server stability under parallel load
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
    client.connection_timeout = 20

    try:
        await client.start()

        # Generate unique keys and values
        operations = [(f"key-{i}", f"value-{i}".encode()) for i in range(num_concurrent_ops)]

        # Concurrent writes to different keys
        await asyncio.gather(*[client.put(key, value) for key, value in operations])

        # Concurrent reads - all should succeed
        results = await asyncio.gather(*[client.get(key) for key, _ in operations])

        # Verify all values are correct
        for i, result in enumerate(results):
            expected = f"value-{i}".encode()
            assert result == expected, f"Key key-{i}: expected {expected}, got {result}"

    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
async def test_connection_pool_exhaustion() -> None:
    """
    Test creating many sequential connections to detect resource leaks.

    Not property-based, but tests resource management.
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    # Create and close many clients sequentially
    for i in range(20):
        client = KVClient(
            server_path=str(go_server),
            tls_mode="disabled",  # Faster for this test
        )
        client.connection_timeout = 10

        try:
            await client.start()
            await client.put(f"stress-{i}", f"value-{i}".encode())
            result = await client.get(f"stress-{i}")
            assert result == f"value-{i}".encode()
        finally:
            await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    num_readers=st.integers(min_value=3, max_value=8),
    key=st.text(min_size=1, max_size=50, alphabet=SAFE_KEY_ALPHABET),
    value=st.binary(min_size=0, max_size=5000),
)
@settings(
    max_examples=10,
    deadline=60000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_concurrent_readers(num_readers: int, key: str, value: bytes) -> None:
    """
    Property test: Multiple concurrent readers should all get the same value.

    Tests for:
    - Read consistency
    - No corruption during concurrent reads
    - Server stability under read load
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    writer = KVClient(
        server_path=str(go_server),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="P-256",
    )
    writer.connection_timeout = 15

    readers = []
    try:
        # Setup: Write initial value
        await writer.start()
        await writer.put(key, value)

        # Create multiple reader clients
        for _ in range(num_readers):
            reader = KVClient(
                server_path=str(go_server),
                tls_mode="auto",
                tls_key_type="ec",
                tls_curve="P-256",
            )
            reader.connection_timeout = 15
            readers.append(reader)

        # Start all readers
        await asyncio.gather(*[reader.start() for reader in readers])

        # Concurrent reads
        results = await asyncio.gather(*[reader.get(key) for reader in readers])

        # All readers should see the same value
        for i, result in enumerate(results):
            assert result == value, f"Reader {i}: expected {value}, got {result}"

    finally:
        await writer.close()
        await asyncio.gather(*[reader.close() for reader in readers], return_exceptions=True)


# 🥣🔬🔚

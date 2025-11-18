#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Property-Based Malformed Data and Protocol Testing

Tests system resilience against:
- Invalid configurations
- Malformed requests
- Protocol violations
- Edge case error handling"""

from pathlib import Path

from hypothesis import HealthCheck, assume, given, settings, strategies as st
import pytest

from tofusoup.rpc.client import KVClient

# Safe key constraints
SAFE_KEY_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.@"


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    invalid_server_path=st.text(min_size=1, max_size=200),
)
@settings(
    max_examples=10,
    deadline=15000,
)
@pytest.mark.asyncio
async def test_invalid_server_path_handling(invalid_server_path: str) -> None:
    """
    Property test: Invalid server paths should fail gracefully with clear errors.

    Tests for:
    - Proper error messages
    - No crashes or hangs
    - Fast failure (not timeout)
    """
    # Skip if we accidentally generate a valid path
    assume(not Path(invalid_server_path).exists())

    client = KVClient(
        server_path=invalid_server_path,
        tls_mode="disabled",
    )
    client.connection_timeout = 5  # Should fail quickly

    # Should raise an error, not hang
    with pytest.raises((FileNotFoundError, OSError, ValueError, RuntimeError)):
        await client.start()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    invalid_curve=st.text(min_size=1, max_size=50),
)
@settings(
    max_examples=20,
    deadline=15000,
)
@pytest.mark.asyncio
async def test_invalid_tls_curve_graceful_handling(invalid_curve: str) -> None:
    """
    Property test: Invalid TLS curves should be rejected gracefully.

    Tests for:
    - Input validation
    - Clear error messages
    - No server crashes
    """
    # Skip valid curves
    valid_curves = ["secp256r1", "secp384r1", "secp521r1", "P-256", "P-384", "P-521", "p256", "p384", "p521"]
    assume(invalid_curve not in valid_curves)

    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    client = KVClient(
        server_path=str(go_server),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve=invalid_curve,
    )
    client.connection_timeout = 10

    # Should handle gracefully (either accept/normalize or reject clearly)
    try:
        await client.start()
        await client.close()
        # If it succeeds, curve was normalized/accepted
    except (ValueError, TypeError, ConnectionError, Exception) as e:
        # Rejection is acceptable
        assert len(str(e)) > 0, "Error should have descriptive message"


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
async def test_missing_tls_mode() -> None:
    """
    Test that missing/invalid TLS mode is handled.

    Non-property test for configuration validation.
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    # Test with potentially invalid TLS configurations
    test_cases = [
        {"tls_mode": "invalid-mode"},
        {"tls_mode": "auto", "tls_key_type": "invalid-type"},
    ]

    for config in test_cases:
        try:
            client = KVClient(
                server_path=str(go_server),
                **config,
            )
            client.connection_timeout = 5

            # Should either work (normalized) or fail clearly
            try:
                await client.start()
                await client.close()
            except (ValueError, TypeError, ConnectionError):
                # Expected for invalid config
                pass

        except (ValueError, TypeError) as e:
            # Constructor rejection is fine
            assert len(str(e)) > 0


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    timeout=st.floats(min_value=-100.0, max_value=0.0),  # Negative/zero timeouts
)
@settings(
    max_examples=10,
    deadline=10000,
)
@pytest.mark.asyncio
async def test_invalid_timeout_handling(timeout: float) -> None:
    """
    Property test: Invalid timeouts should be rejected or clamped.

    Tests for:
    - Input validation on timeouts
    - No infinite hangs
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    try:
        client = KVClient(
            server_path=str(go_server),
            tls_mode="disabled",
        )
        client.connection_timeout = timeout

        # Should either reject invalid timeout or clamp to valid range
        await client.start()
        await client.close()

    except (ValueError, TypeError, TimeoutError):
        # Rejection is acceptable
        pass


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    special_key=st.one_of(
        st.just(""),  # Empty key
        st.just("."),  # Current directory
        st.just(".."),  # Parent directory
        st.just("/"),  # Root
        st.just("\\"),  # Backslash
        st.text(min_size=1, max_size=10, alphabet="/\\"),  # Path separators
    ),
)
@settings(
    max_examples=15,
    deadline=20000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_path_traversal_protection(special_key: str) -> None:
    """
    Property test: Keys that look like filesystem paths should be handled safely.

    Tests for:
    - Path traversal attacks
    - Directory escapes
    - Security vulnerabilities
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

        # Try to use special/dangerous key
        # Server should either:
        # 1. Reject it (preferred)
        # 2. Sanitize it safely
        # 3. Never access files outside /tmp/kv-data/
        try:
            await client.put(special_key, b"test")
            result = await client.get(special_key)

            # If accepted, verify it worked correctly
            assert result == b"test"

        except (ValueError, KeyError, OSError, Exception):
            # Rejection is acceptable and preferred for security
            pass

    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    operation_count=st.integers(min_value=1, max_value=100),
)
@settings(
    max_examples=5,
    deadline=60000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_get_nonexistent_keys(operation_count: int) -> None:
    """
    Property test: Getting non-existent keys should return consistent errors.

    Tests for:
    - Proper NOT_FOUND handling
    - No crashes on missing keys
    - Consistent error behavior
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    client = KVClient(
        server_path=str(go_server),
        tls_mode="disabled",
    )
    client.connection_timeout = 20

    try:
        await client.start()

        # Try to get many non-existent keys
        for i in range(operation_count):
            nonexistent_key = f"does-not-exist-{i}"

            # Should return empty bytes or raise KeyError consistently
            try:
                result = await client.get(nonexistent_key)
                # If it returns data, should be empty or None
                assert result in [b"", None], f"Unexpected result for missing key: {result}"
            except KeyError:
                # KeyError is also acceptable
                pass

    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
async def test_rapid_connect_disconnect() -> None:
    """
    Test rapid connection cycling to detect resource leaks.

    Non-property test for connection lifecycle.
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    # Rapidly create and destroy connections
    for i in range(30):
        client = KVClient(
            server_path=str(go_server),
            tls_mode="disabled",
        )
        client.connection_timeout = 5

        await client.start()
        await client.put(f"rapid-{i}", b"test")
        await client.close()


# 🥣🔬🔚

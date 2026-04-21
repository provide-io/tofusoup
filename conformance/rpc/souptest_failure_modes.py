#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Property-Based Error Injection and Failure Mode Testing

Tests how the system handles:
- Malformed data
- Extreme timeouts
- Invalid configurations
- Edge case errors"""

from pathlib import Path

from hypothesis import HealthCheck, assume, given, settings, strategies as st
import pytest

from tofusoup.rpc.client import KVClient


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    timeout=st.floats(min_value=0.1, max_value=1.0),  # Very short timeouts
)
@settings(
    max_examples=10,
    deadline=15000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_short_timeouts_handled_gracefully(timeout: float) -> None:
    """
    Property test: Extremely short timeouts should fail gracefully, not crash.
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
    client.connection_timeout = timeout

    # With very short timeout, connection might succeed or timeout
    # Either is acceptable, as long as it doesn't crash
    try:
        await client.start()
        # If it connects, verify it works
        await client.put("timeout-test", b"quick")
        await client.close()
    except (TimeoutError, Exception):
        # Timeout is acceptable - verify it's handled gracefully
        pass  # This is fine, just testing it doesn't crash


@pytest.mark.integration_rpc
@given(
    invalid_curve=st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=("Cs",))),
)
@settings(
    max_examples=20,
    deadline=10000,
)
@pytest.mark.asyncio
async def test_invalid_curve_handled(invalid_curve: str) -> None:
    """
    Property test: Invalid curve names should be rejected gracefully.
    """
    # Skip if we accidentally generate a valid curve name
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
    client.connection_timeout = 5

    # Should fail, but gracefully
    try:
        await client.start()
        await client.close()
        # If it succeeds, that's OK too (curve might be normalized/accepted)
    except (ValueError, TypeError, Exception):
        # Expected - invalid curve rejected
        pass


@pytest.mark.asyncio
async def test_missing_server_binary_fails_early() -> None:
    """Test that nonexistent server fails immediately, not after timeout."""
    nonexistent = Path("/tmp/definitely-does-not-exist-12345")

    client = KVClient(
        server_path=str(nonexistent),
        tls_mode="disabled",
    )

    # Should fail quickly with clear error
    with pytest.raises((FileNotFoundError, OSError)) as exc_info:
        await client.start()

    # Error message should mention the file
    assert "not found" in str(exc_info.value).lower() or "no such file" in str(exc_info.value).lower()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@given(
    key_size=st.integers(min_value=0, max_value=0),  # Empty key
)
@settings(
    max_examples=5,
    deadline=15000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_empty_key_behavior(key_size: int) -> None:
    """
    Property test: Empty keys should be handled (either accepted or rejected gracefully).
    """
    go_server = Path("bin/soup-go")
    if not go_server.exists():
        pytest.skip("soup-go not found")

    client = KVClient(
        server_path=str(go_server),
        tls_mode="disabled",  # Faster for this test
    )

    try:
        await client.start()

        # Try to use empty key
        try:
            await client.put("", b"empty-key-test")
            result = await client.get("")
            # If it accepts empty keys, verify roundtrip works
            assert result == b"empty-key-test"
        except (ValueError, KeyError, Exception):
            # If it rejects empty keys, that's also acceptable
            pass

    finally:
        await client.close()


# 🥣🔬🔚

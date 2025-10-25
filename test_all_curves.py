#!/usr/bin/env python3
"""
Test Python client → Go server with all supported elliptic curves
Tests: secp256r1, secp384r1, secp521r1, and auto mode
"""
import asyncio
import builtins
import contextlib
from pathlib import Path
import sys
import time

from tofusoup.rpc.client import KVClient


async def test_curve(curve_name: str, soup_go_path: Path) -> tuple[bool, float, str]:
    """
    Test a specific curve configuration.

    Returns:
        (success, duration, error_message)
    """
    print(f"\n{'='*70}")
    print(f"Test: Python Client → Go Server with {curve_name}")
    print(f"{'='*70}")

    start_time = time.time()

    try:
        # Create client with specified curve
        client = KVClient(
            server_path=str(soup_go_path),
            tls_mode="auto",
            tls_key_type="ec",
            tls_curve=curve_name
        )

        print(f"⏳ Starting client with curve: {curve_name}")
        await client.start()
        connection_time = time.time() - start_time
        print(f"✅ Connected successfully in {connection_time:.2f}s")

        # Test Put operation
        test_key = f"test-{curve_name}-py2go"
        test_value = f"Hello from Python client with {curve_name}!".encode()

        print(f"📤 PUT: key='{test_key}'")
        await client.put(test_key, test_value)
        print("✅ Put successful")

        # Test Get operation
        print(f"📥 GET: key='{test_key}'")
        result = await client.get(test_key)
        print(f"✅ Got {len(result)} bytes")

        # Verify data
        if result == test_value:
            duration = time.time() - start_time
            print(f"🎉 SUCCESS: Value matches! (total: {duration:.2f}s)")
            print(f"   Retrieved: {result.decode()}")
            await client.close()
            return (True, duration, "")
        else:
            print("❌ FAILURE: Value mismatch!")
            await client.close()
            return (False, time.time() - start_time, "Value mismatch")

    except TimeoutError:
        duration = time.time() - start_time
        error = f"Connection timeout after {duration:.2f}s"
        print(f"❌ {error}")
        with contextlib.suppress(builtins.BaseException):
            await client.close()
        return (False, duration, error)

    except Exception as e:
        duration = time.time() - start_time
        error = f"{type(e).__name__}: {e}"
        print(f"❌ ERROR: {error}")
        with contextlib.suppress(builtins.BaseException):
            await client.close()
        return (False, duration, error)


async def main() -> int:
    """Run all curve tests."""
    soup_go_path = Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go")

    if not soup_go_path.exists():
        print(f"❌ Go server not found: {soup_go_path}")
        return 1

    print("\n" + "="*70)
    print("ELLIPTIC CURVE COMPATIBILITY TEST SUITE")
    print("Python Client → Go Server (pyvider-rpcplugin ↔ go-plugin)")
    print("="*70)
    print(f"\nGo Server: {soup_go_path}")
    print("TLS Mode: auto (mTLS with TLSProvider)")
    print("Transport: TCP (forced via PLUGIN_MIN_PORT/MAX_PORT)")
    print()

    # Test all curves
    curves_to_test = [
        ("secp256r1", "NIST P-256"),
        ("secp384r1", "NIST P-384"),
        ("secp521r1", "NIST P-521"),
        ("auto", "go-plugin default (P-521)")
    ]

    results = []

    for curve, description in curves_to_test:
        success, duration, error = await test_curve(curve, soup_go_path)
        results.append((curve, description, success, duration, error))

        # Small delay between tests
        if curve != curves_to_test[-1][0]:
            await asyncio.sleep(1)

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print()

    passed = 0
    failed = 0

    for curve, description, success, duration, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}  {curve:12s} ({description:30s}) {duration:6.2f}s")
        if error:
            print(f"       Error: {error}")

        if success:
            passed += 1
        else:
            failed += 1

    print()
    print(f"Total: {len(results)} tests, {passed} passed, {failed} failed")
    print("="*70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

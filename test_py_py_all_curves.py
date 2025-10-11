#!/usr/bin/env python3
"""
Test Python client → Python server with all curves
"""
import asyncio
import sys
import time
from pathlib import Path
from tofusoup.rpc.client import KVClient


async def test_curve(curve_name: str, soup_path: Path) -> tuple[bool, float, str]:
    """Test a specific curve."""
    print(f"\n{'='*70}")
    print(f"Testing: Python → Python with {curve_name}")
    print(f"{'='*70}")

    client = KVClient(
        server_path=str(soup_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve=curve_name
    )
    client.connection_timeout = 10

    try:
        start = time.time()
        print(f"⏳ Connecting with {curve_name}...")

        await client.start()
        connect_time = time.time() - start
        print(f"✅ Connected in {connect_time:.2f}s")

        # Test operations
        test_key = f"test-{curve_name}"
        test_value = f"Hello with {curve_name}!".encode()

        await client.put(test_key, test_value)
        print(f"✅ PUT successful")

        result = await client.get(test_key)
        print(f"✅ GET successful: {len(result)} bytes")

        if result == test_value:
            total_time = time.time() - start
            print(f"\n🎉 SUCCESS: {curve_name} works! (total: {total_time:.2f}s)")
            await client.close()
            return (True, total_time, "")
        else:
            print(f"\n❌ FAIL: Value mismatch")
            await client.close()
            return (False, time.time() - start, "Value mismatch")

    except Exception as e:
        error = f"{type(e).__name__}: {str(e)[:100]}"
        print(f"\n❌ FAIL: {error}")
        try:
            await client.close()
        except:
            pass
        return (False, time.time() - start, error)


async def main():
    soup_path = Path("/Users/tim/code/gh/provide-io/pyvider/.venv/bin/soup")

    if not soup_path.exists():
        print(f"❌ Python server not found: {soup_path}")
        return 1

    print("\n" + "="*70)
    print("ELLIPTIC CURVE TEST: Python → Python")
    print("="*70)
    print(f"\nServer: {soup_path}")
    print()

    # Test curves supported by Python's cryptography library
    # Note: secp521r1 not supported by grpcio
    curves_to_test = [
        ("secp256r1", "NIST P-256"),
        ("secp384r1", "NIST P-384"),
    ]

    results = []

    for curve, description in curves_to_test:
        success, duration, error = await test_curve(curve, soup_path)
        results.append((curve, description, success, duration, error))
        await asyncio.sleep(0.5)

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

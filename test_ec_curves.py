#!/usr/bin/env python3
"""
Test all EC curves (P-256, P-384, P-521) with Python client → Go server
"""
import asyncio
import time
from tofusoup.rpc.client import KVClient


async def test_curve(curve_name: str, soup_go_path: str) -> dict:
    """Test a specific EC curve."""
    print(f"\n{'='*60}")
    print(f"Testing {curve_name} curve")
    print(f"{'='*60}")

    start_time = time.time()
    client = KVClient(
        server_path=soup_go_path,
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve=curve_name
    )

    try:
        print(f"⏳ Starting client with {curve_name}...")
        await client.start()

        print(f"✅ Client started successfully!")

        # Test put/get operations
        test_key = f"test-{curve_name.lower()}"
        test_value = f"Hello from {curve_name}!".encode()

        print(f"📤 Putting key='{test_key}', value={len(test_value)} bytes...")
        await client.put(test_key, test_value)

        print(f"📥 Getting key='{test_key}'...")
        result = await client.get(test_key)

        duration = time.time() - start_time

        if result == test_value:
            print(f"✅ SUCCESS: Value matches! ({duration:.2f}s)")
            return {
                "curve": curve_name,
                "success": True,
                "duration": duration,
                "error": None
            }
        else:
            print(f"❌ FAILURE: Value mismatch! ({duration:.2f}s)")
            print(f"   Expected: {test_value}")
            print(f"   Got: {result}")
            return {
                "curve": curve_name,
                "success": False,
                "duration": duration,
                "error": "Value mismatch"
            }

    except asyncio.TimeoutError:
        duration = time.time() - start_time
        print(f"⏱️ TIMEOUT: Connection failed after {duration:.2f}s")
        return {
            "curve": curve_name,
            "success": False,
            "duration": duration,
            "error": "Connection timeout"
        }

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)

        # Check for known P-521 incompatibility
        if curve_name == "P-521" and ("secp521r1" in error_msg or "P-521" in error_msg):
            print(f"❌ EXPECTED FAILURE: Python client incompatible with {curve_name}")
            print(f"   Error: {error_msg[:100]}")
        else:
            print(f"❌ ERROR after {duration:.2f}s: {type(e).__name__}: {error_msg[:100]}")

        return {
            "curve": curve_name,
            "success": False,
            "duration": duration,
            "error": error_msg
        }

    finally:
        try:
            await client.close()
            print("🔒 Client closed")
        except Exception:
            pass


async def main():
    """Run all curve tests."""
    soup_go_path = "/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go"

    print("\n🔐 EC Curve Compatibility Test")
    print("Testing Python Client → Go Server")
    print(f"Server: {soup_go_path}\n")

    # Test all three NIST curves
    curves = ["P-256", "P-384", "P-521"]
    results = []

    for curve in curves:
        result = await test_curve(curve, soup_go_path)
        results.append(result)
        await asyncio.sleep(0.5)  # Brief pause between tests

    # Summary report
    print("\n" + "="*60)
    print("📊 Test Results Summary")
    print("="*60)

    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        duration = f"({result['duration']:.2f}s)"
        print(f"{result['curve']:8} | {status} {duration}")
        if result["error"] and not result["success"]:
            error_preview = result["error"][:60]
            print(f"         | Error: {error_preview}...")

    # Statistics
    passed = sum(1 for r in results if r["success"])
    total = len(results)

    print(f"\n{'='*60}")
    print(f"Total: {passed}/{total} curves working")
    print(f"Success rate: {passed/total*100:.1f}%")
    print(f"\n💡 Note: P-521 is known to be incompatible with Python client")
    print(f"   due to secp521r1 curve support differences")


if __name__ == "__main__":
    asyncio.run(main())

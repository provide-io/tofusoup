#!/usr/bin/env python3
"""
Test a single curve: Python client → Go server
Usage: python test_curve.py <curve_name>
"""
import asyncio
import sys
import time
from pathlib import Path
from tofusoup.rpc.client import KVClient


async def test_curve(curve_name: str) -> int:
    soup_go_path = Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go")

    print(f"\n{'='*70}")
    print(f"Testing curve: {curve_name}")
    print(f"{'='*70}\n")

    client = KVClient(
        server_path=str(soup_go_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve=curve_name
    )
    client.connection_timeout = 15

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
            return 0
        else:
            print(f"\n❌ FAIL: Value mismatch")
            await client.close()
            return 1

    except Exception as e:
        print(f"\n❌ FAIL: {type(e).__name__}: {str(e)[:100]}")
        try:
            await client.close()
        except:
            pass
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_curve.py <curve_name>")
        print("Curves: secp256r1, secp384r1, secp521r1")
        sys.exit(1)

    curve = sys.argv[1]
    exit_code = asyncio.run(test_curve(curve))
    sys.exit(exit_code)

# test_rpc_combos.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

Quick RPC combination tests:
1. Python client → Python server
2. Go client → Python server (via CLI)
"""
import asyncio
import time
from tofusoup.rpc.client import KVClient


async def test_python_to_python():
    """Test Python client → Python server with RSA 2048."""
    print("=" * 60)
    print("🐍→🐍 Testing Python Client → Python Server")
    print("=" * 60)

    start_time = time.time()
    client = KVClient(
        server_path="soup",  # Use soup from PATH
        tls_mode="auto",
        tls_key_type="rsa"
    )

    try:
        print("⏳ Starting client (timeout: 10s)...")
        await asyncio.wait_for(client.start(), timeout=10.0)

        print("✅ Client started successfully!")

        # Test put/get operations
        test_key = "test-pypy"
        test_value = b"Hello from Python to Python!"

        print(f"📤 Putting key='{test_key}', value={len(test_value)} bytes...")
        await client.put(test_key, test_value)

        print(f"📥 Getting key='{test_key}'...")
        result = await client.get(test_key)

        duration = time.time() - start_time

        if result == test_value:
            print(f"✅ SUCCESS: Value matches! ({duration:.2f}s)")
            return True
        else:
            print(f"❌ FAILURE: Value mismatch! ({duration:.2f}s)")
            print(f"   Expected: {test_value}")
            print(f"   Got: {result}")
            return False

    except asyncio.TimeoutError:
        duration = time.time() - start_time
        print(f"⏱️ TIMEOUT: Handshake failed after {duration:.2f}s")
        print("   This is the known Python→Python handshake issue")
        return False

    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ ERROR after {duration:.2f}s: {type(e).__name__}: {e}")
        return False

    finally:
        try:
            await client.close()
            print("🔒 Client closed")
        except Exception:
            pass


async def main():
    """Run all tests."""
    print("\n🍲 TofuSoup RPC Combination Tests\n")

    # Test 1: Python → Python
    py_to_py_result = await test_python_to_python()

    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    print(f"Python → Python: {'✅ PASS' if py_to_py_result else '❌ FAIL'}")

    print("\nNote: Go client → Python server test will be run via CLI separately")


if __name__ == "__main__":
    asyncio.run(main())


# 🍜🍲🤔🪄

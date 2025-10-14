# test_py_to_go_secp384r1.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

Test Python client → Go server with secp384r1 curve on both sides
"""
import asyncio
import time
from pathlib import Path
from tofusoup.rpc.client import KVClient


async def main():
    """Test Python client → Go server with secp384r1 curve."""
    soup_go_path = Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go")

    print("="*70)
    print("Test: Python Client → Go Server with secp384r1 Curve")
    print("="*70)
    print()
    print(f"ℹ️  Go server: {soup_go_path}")
    print(f"ℹ️  TLS Mode: auto (mTLS with TLSProvider)")
    print(f"ℹ️  Key Type: EC")
    print(f"ℹ️  Curve: secp384r1")
    print()

    start_time = time.time()

    # Create client with secp384r1 curve
    client = KVClient(
        server_path=str(soup_go_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="secp384r1"  # Use secp384r1 curve
    )

    try:
        print("⏳ Starting Python client with secp384r1 curve...")
        await client.start()
        print(f"✅ Client connected successfully! ({time.time() - start_time:.2f}s)")
        print()

        # Test Put operation
        test_key = "test-secp384r1-py2go"
        test_value = b"Hello from Python client with secp384r1 curve!"

        print(f"📤 PUT: key='{test_key}', value={len(test_value)} bytes")
        await client.put(test_key, test_value)
        print("✅ Put successful")
        print()

        # Test Get operation
        print(f"📥 GET: key='{test_key}'")
        result = await client.get(test_key)
        print(f"✅ Get successful: {len(result)} bytes retrieved")
        print()

        # Verify data
        if result == test_value:
            duration = time.time() - start_time
            print(f"🎉 SUCCESS: Value matches! ({duration:.2f}s)")
            print(f"   Retrieved: {result.decode()}")
            print()
            print("✅ Test PASSED!")
            return 0
        else:
            print("❌ FAILURE: Value mismatch!")
            print(f"   Expected: {test_value}")
            print(f"   Got: {result}")
            return 1

    except asyncio.TimeoutError:
        duration = time.time() - start_time
        print(f"❌ TIMEOUT: Connection failed after {duration:.2f}s")
        return 1

    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ ERROR after {duration:.2f}s:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        try:
            await client.close()
            print("🔒 Client closed")
        except Exception:
            pass


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)


# 🍜🍲🤔🪄

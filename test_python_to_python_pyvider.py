#!/usr/bin/env python3
"""Test Python client → Python server using pyvider-rpcplugin infrastructure."""
from __future__ import annotations

import asyncio
import time


async def main():
    from tofusoup.rpc.client import KVClient

    print("="*70)
    print("Test: Python Client → Python Server (pyvider-rpcplugin)")
    print("="*70)
    print()

    # Use the soup command in PATH
    soup_path = "soup"

    print(f"ℹ️  Using soup server: {soup_path}")
    print()

    start = time.time()
    client = KVClient(
        server_path=soup_path,
        tls_mode="auto",
        tls_key_type="ec",  # Use EC for compatibility
        tls_curve="P-384",  # Match what pyvider uses
    )

    try:
        print("⏳ Starting client (timeout: 15s)...")
        await asyncio.wait_for(client.start(), timeout=15.0)
        print(f"✅ Connected! ({time.time() - start:.2f}s)\n")

        # Test put
        key = "test-py2py"
        value = b"Hello from Python to Python!"

        print(f"📤 PUT: key='{key}', value={value}")
        await client.put(key, value)
        print("✅ Put successful\n")

        # Test get
        print(f"📥 GET: key='{key}'")
        result = await client.get(key)
        print(f"✅ Got: {result}")

        if result == value:
            print("\n🎉 SUCCESS: Python → Python works!")
            return True
        else:
            print(f"\n❌ FAIL: Expected {value}, got {result}")
            return False

    except asyncio.TimeoutError:
        print(f"❌ Timeout after {time.time() - start:.2f}s")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.close()


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)

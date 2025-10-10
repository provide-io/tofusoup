#!/usr/bin/env python3
"""Simple Python → Go test with TLS disabled."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path


async def main():
    from tofusoup.rpc.client import KVClient

    soup_go_path = Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go")

    print("Testing Python client → Go server (TLS disabled)")
    print(f"Using soup-go: {soup_go_path}\n")

    # Try with TLS disabled first
    client = KVClient(
        server_path=str(soup_go_path),
        tls_mode="disabled"  # Disable TLS to test basic connectivity
    )

    start = time.time()
    try:
        print("⏳ Starting client (TLS disabled, timeout: 15s)...")
        await asyncio.wait_for(client.start(), timeout=15.0)
        print(f"✅ Connected! ({time.time() - start:.2f}s)\n")

        # Test put
        key = "test-simple"
        value = b"Hello!"

        print(f"📤 PUT: key='{key}', value={value}")
        await client.put(key, value)
        print("✅ Put successful\n")

        # Test get
        print(f"📥 GET: key='{key}'")
        result = await client.get(key)
        print(f"✅ Got: {result}")

        if result == value:
            print("\n🎉 SUCCESS: Value matches!")
        else:
            print(f"\n❌ FAIL: Expected {value}, got {result}")

    except asyncio.TimeoutError:
        print(f"❌ Timeout after {time.time() - start:.2f}s")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

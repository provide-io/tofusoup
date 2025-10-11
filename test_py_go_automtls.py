#!/usr/bin/env python3
"""
Test Python client → Go server with AutoMTLS (go-plugin default)
"""
import asyncio
import time
from pathlib import Path
from tofusoup.rpc.client import KVClient


async def main():
    soup_go_path = Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go")

    print("Testing Python client → Go server (AutoMTLS/auto mode)")
    print()

    # Test with "auto" curve (go-plugin's default AutoMTLS with P-521)
    client = KVClient(
        server_path=str(soup_go_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="auto"  # Use go-plugin AutoMTLS default
    )
    client.connection_timeout = 10

    try:
        print("⏳ Connecting with auto/AutoMTLS...")
        start = time.time()
        await client.start()
        print(f"✅ Connected in {time.time() - start:.2f}s")

        await client.put("test_key", b"test_value_automtls")
        result = await client.get("test_key")
        print(f"✅ Put/Get successful: {result}")

        await client.close()
        print(f"\n🎉 SUCCESS! Python → Go works with AutoMTLS")
        return 0

    except Exception as e:
        print(f"\n❌ FAIL: {type(e).__name__}: {str(e)[:200]}")
        try:
            await client.close()
        except:
            pass
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

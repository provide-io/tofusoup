#!/usr/bin/env python3
"""
Test Python client → Python server
"""
import asyncio
import time
from pathlib import Path
from tofusoup.rpc.client import KVClient


async def main():
    # Use the Python 'soup' command as server
    soup_path = Path("/Users/tim/code/gh/provide-io/pyvider/.venv/bin/soup")

    print("Testing Python client → Python server")
    print()

    # Test with auto mode
    client = KVClient(
        server_path=str(soup_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="secp384r1"
    )
    client.connection_timeout = 10

    try:
        print("⏳ Connecting...")
        start = time.time()
        await client.start()
        print(f"✅ Connected in {time.time() - start:.2f}s")

        await client.put("test_key", b"test_value_py2py")
        result = await client.get("test_key")
        print(f"✅ Put/Get successful: {result}")

        await client.close()
        print(f"\n🎉 SUCCESS! Python → Python works")
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

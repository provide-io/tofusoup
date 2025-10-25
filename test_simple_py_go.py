#!/usr/bin/env python3
"""
Simple test: Python client → Go server
"""
import asyncio
import builtins
import contextlib
import os
from pathlib import Path
import time

from tofusoup.rpc.client import KVClient

# Enable debug logging
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["PYVIDER_LOG_LEVEL"] = "DEBUG"


async def main() -> int | None:
    soup_go_path = Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go")

    print("Testing Python client → Go server")
    print(f"Server: {soup_go_path}")
    print()

    # Test with secp384r1
    client = KVClient(
        server_path=str(soup_go_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="secp384r1"
    )

    # Reduce timeout for faster feedback
    client.connection_timeout = 10

    try:
        print("⏳ Connecting...")
        start = time.time()
        await client.start()
        print(f"✅ Connected in {time.time() - start:.2f}s")

        # Simple Put/Get
        await client.put("test_key", b"test_value")
        result = await client.get("test_key")
        print(f"✅ Put/Get successful: {result}")

        await client.close()
        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        with contextlib.suppress(builtins.BaseException):
            await client.close()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

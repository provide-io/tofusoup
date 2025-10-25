#!/usr/bin/env python3
"""
Test Python client → Go server with auto mode (no specific curve)
"""
import asyncio
import builtins
import contextlib
from pathlib import Path
import time

from tofusoup.rpc.client import KVClient


async def main() -> int | None:
    soup_go_path = Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go")

    print("Testing Python client → Go server (auto mode)")
    print()

    # Test with "auto" curve (should use go-plugin's AutoMTLS)
    client = KVClient(
        server_path=str(soup_go_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="auto"  # Use go-plugin default
    )

    client.connection_timeout = 10

    try:
        print("⏳ Connecting with auto mode...")
        start = time.time()
        await client.start()
        print(f"✅ Connected in {time.time() - start:.2f}s")

        await client.put("test_key", b"test_value")
        result = await client.get("test_key")
        print(f"✅ Put/Get successful: {result}")

        await client.close()
        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        with contextlib.suppress(builtins.BaseException):
            await client.close()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

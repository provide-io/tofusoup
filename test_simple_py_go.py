# test_simple_py_go.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

Simple test: Python client → Go server
"""
import asyncio
import os
import time
from pathlib import Path
from tofusoup.rpc.client import KVClient

# Enable debug logging
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["PYVIDER_LOG_LEVEL"] = "DEBUG"


async def main():
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
        try:
            await client.close()
        except:
            pass
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)


# 🍜🍲🤔🪄

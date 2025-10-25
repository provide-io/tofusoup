#!/usr/bin/env python3
"""
Test Python client → Python server
"""
import asyncio
import builtins
import contextlib
from pathlib import Path
import time

from provide.foundation import perr, pout

from tofusoup.rpc.client import KVClient


async def main() -> int | None:
    # Use the Python 'soup' command as server
    soup_path = Path("/Users/tim/code/gh/provide-io/pyvider/.venv/bin/soup")

    pout("=" * 70)
    pout("Testing: Python client → Python server", color="cyan", bold=True)
    pout("=" * 70)
    pout("")
    pout("✓ This is a SUPPORTED configuration", color="green", bold=True)
    pout("  - Python → Python works with all supported curves")
    pout("  - Supported curves: secp256r1, secp384r1")
    pout("")
    pout("Note: Python → Go is NOT supported (known issue in pyvider-rpcplugin)", color="yellow")
    pout("      Use Go → Python instead for cross-language scenarios", color="yellow")
    pout("")

    # Test with auto mode
    client = KVClient(
        server_path=str(soup_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="secp384r1"
    )
    client.connection_timeout = 10

    try:
        pout("⏳ Connecting with curve secp384r1...", color="cyan")
        start = time.time()
        await client.start()
        pout(f"✅ Connected in {time.time() - start:.2f}s", color="green")

        await client.put("test_key", b"test_value_py2py")
        result = await client.get("test_key")
        pout(f"✅ Put/Get successful: {result}", color="green")

        await client.close()
        pout("")
        pout("=" * 70)
        pout("🎉 SUCCESS! Python → Python connection works perfectly", color="green", bold=True)
        pout("=" * 70)
        pout("")
        pout("See docs/rpc-compatibility-matrix.md for full compatibility details", color="cyan")
        return 0

    except Exception as e:
        pout("")
        pout("=" * 70)
        perr(f"❌ FAIL: {type(e).__name__}: {str(e)[:200]}", color="red", bold=True)
        pout("=" * 70)
        with contextlib.suppress(builtins.BaseException):
            await client.close()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

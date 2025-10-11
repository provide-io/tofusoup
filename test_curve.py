#!/usr/bin/env python3
"""
Test a single curve: Python client → Go server

⚠️  WARNING: Python → Go connections are NOT SUPPORTED ⚠️

This script tests Python client → Go server, which is a known bug in
pyvider-rpcplugin. These tests are expected to FAIL with timeout errors.

For testing working configurations, see:
- test_py_to_py.py (Python → Python) ✓ SUPPORTED
- Go client → Python server ✓ SUPPORTED

Usage: python test_curve.py <curve_name>
"""
import asyncio
import sys
import time
from pathlib import Path
from provide.foundation import pout, perr
from tofusoup.rpc.client import KVClient


async def test_curve(curve_name: str) -> int:
    soup_go_path = Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go")

    pout(f"\n{'='*70}")
    perr(f"⚠️  WARNING: Testing Python → Go (UNSUPPORTED)", color="yellow", bold=True)
    pout(f"{'='*70}")
    pout("")
    perr("❌ This configuration is NOT SUPPORTED due to a known bug", color="red", bold=True)
    pout("   in pyvider-rpcplugin. Connection will likely TIMEOUT.", color="yellow")
    pout("")
    pout("✓ Supported alternatives:", color="green")
    pout("  - Python → Python (use test_py_to_py.py)")
    pout("  - Go → Python (use Go client)")
    pout("  - Go → Go")
    pout("")
    pout(f"Testing curve: {curve_name}", color="cyan")
    pout(f"{'='*70}\n")

    client = KVClient(
        server_path=str(soup_go_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve=curve_name
    )
    client.connection_timeout = 15

    try:
        start = time.time()
        pout(f"⏳ Connecting with {curve_name}...", color="cyan")

        await client.start()
        connect_time = time.time() - start
        pout(f"✅ Connected in {connect_time:.2f}s", color="green")

        # Test operations
        test_key = f"test-{curve_name}"
        test_value = f"Hello with {curve_name}!".encode()

        await client.put(test_key, test_value)
        pout(f"✅ PUT successful", color="green")

        result = await client.get(test_key)
        pout(f"✅ GET successful: {len(result)} bytes", color="green")

        if result == test_value:
            total_time = time.time() - start
            pout(f"\n🎉 SUCCESS: {curve_name} works! (total: {total_time:.2f}s)", color="green", bold=True)
            await client.close()
            return 0
        else:
            perr(f"\n❌ FAIL: Value mismatch", color="red", bold=True)
            await client.close()
            return 1

    except Exception as e:
        perr(f"\n❌ FAIL: {type(e).__name__}: {str(e)[:100]}", color="red", bold=True)
        pout("")
        pout("=" * 70)
        pout("⚠️  This failure is EXPECTED - Python → Go is not supported", color="yellow", bold=True)
        pout("=" * 70)
        pout("")
        pout("This is a known issue in pyvider-rpcplugin.", color="yellow")
        pout("")
        pout("For working configurations, use:", color="green")
        pout("  ✓ Python → Python (test_py_to_py.py)")
        pout("  ✓ Go → Python")
        pout("")
        pout("See docs/rpc-compatibility-matrix.md for details", color="cyan")
        try:
            await client.close()
        except:
            pass
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        pout("")
        pout("=" * 70)
        perr("⚠️  WARNING: Python → Go connections are NOT SUPPORTED", color="yellow", bold=True)
        pout("=" * 70)
        pout("")
        pout("Usage: python test_curve.py <curve_name>", color="cyan")
        pout("Curves: secp256r1, secp384r1, secp521r1")
        pout("")
        pout("Note: This test is expected to FAIL due to known pyvider bug.", color="yellow")
        pout("      Use test_py_to_py.py for testing working configurations.", color="yellow")
        pout("")
        sys.exit(1)

    curve = sys.argv[1]
    pout("")
    pout("⚠️  Note: This test attempts Python → Go, which is NOT SUPPORTED", color="yellow", bold=True)
    pout("")
    exit_code = asyncio.run(test_curve(curve))
    sys.exit(exit_code)

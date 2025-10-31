#!/usr/bin/env python3
"""Test all TLS certificate type combinations between client and server."""

import subprocess
import os
import sys
from pathlib import Path

# Test configurations
configs = [
    {"key_type": "rsa", "curve": None, "label": "RSA-2048"},
    {"key_type": "ecdsa", "curve": "secp256r1", "label": "ECDSA P-256"},
    {"key_type": "ecdsa", "curve": "secp384r1", "label": "ECDSA P-384"},
    {"key_type": "ecdsa", "curve": "secp521r1", "label": "ECDSA P-521"},
]

sys.path.insert(0, str(Path(__file__).parent / "src"))

import asyncio
from tofusoup.rpc.client import KVClient

async def test_config(config):
    """Test a specific server certificate configuration."""
    server_path = Path(__file__).parent / ".venv" / "bin" / "soup"

    client = KVClient(
        server_path=str(server_path),
        tls_mode="auto",
        tls_key_type=config["key_type"],
        tls_curve=config["curve"] if config["curve"] else "secp384r1",
    )

    try:
        print(f"Testing {config['label']}...", end=" ", flush=True)
        await asyncio.wait_for(client.start(), timeout=5.0)

        # If we get here, connection succeeded!
        await client.put("test", b"works")
        result = await client.get("test")

        if result == b"works":
            print("✅ SUCCESS")
            return True
        else:
            print("⚠️  Connected but data mismatch")
            return False

    except asyncio.TimeoutError:
        print("❌ TIMEOUT (channel never ready)")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    finally:
        try:
            await client.close()
        except:
            pass

async def main():
    """Run all test configurations."""
    print("=" * 60)
    print("TLS Certificate Type Compatibility Matrix")
    print("=" * 60)
    print()

    results = {}
    for config in configs:
        success = await test_config(config)
        results[config["label"]] = success
        await asyncio.sleep(0.5)  # Brief pause between tests

    print()
    print("=" * 60)
    print("RESULTS:")
    print("=" * 60)
    for label, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {label:20s} {status}")

    total = len(results)
    passed = sum(results.values())
    print()
    print(f"Total: {passed}/{total} passed")

    return all(results.values())

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

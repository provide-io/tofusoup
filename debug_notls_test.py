#!/usr/bin/env python3
"""Debug script to test Python → Python WITHOUT TLS (baseline)."""

import asyncio
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tofusoup.rpc.client import KVClient


async def main() -> None:
    """Test Python → Python without TLS (should work)."""
    server_path = Path(__file__).parent / ".venv" / "bin" / "soup"

    print("🔍 Testing Python server → Python client WITHOUT TLS (baseline)")
    print(f"🖥️  Server path: {server_path}")
    print()

    client = KVClient(
        server_path=str(server_path),
        tls_mode="disabled",  # NO TLS
    )

    try:
        print("▶️  Starting client...")
        await asyncio.wait_for(client.start(), timeout=10.0)

        print("✅ Client started successfully!")

        # Test operations
        print("\n🔄 Testing Put operation...")
        await client.put("test-key", b"Hello!")
        print("✅ Put succeeded!")

        print("\n🔄 Testing Get operation...")
        value = await client.get("test-key")
        print(f"✅ Get succeeded! Value: {value}")

    except TimeoutError:
        print("❌ TIMEOUT (unexpected - no-TLS should work)")
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        try:
            await client.close()
            print("\n🛑 Client closed")
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Debug script to manually test Python → Python TLS connection.
This will help us see the actual server output and identify the TLS issue.
"""

import asyncio
import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tofusoup.rpc.client import KVClient

# Set DEBUG logging to see everything
os.environ["LOG_LEVEL"] = "DEBUG"


async def main() -> None:
    """Test Python → Python TLS connection."""
    # Use the .venv soup command (Python server)
    server_path = Path(__file__).parent / ".venv" / "bin" / "soup"

    print("🔍 Testing Python server → Python client with TLS")
    print(f"🖥️  Server path: {server_path}")
    print()

    # Create client with TLS enabled (matching test configuration)
    client = KVClient(
        server_path=str(server_path),
        tls_mode="auto",
        tls_key_type="rsa",
    )

    try:
        print("▶️  Starting client (will spawn server subprocess)...")
        await asyncio.wait_for(client.start(), timeout=30.0)

        print("✅ Client started successfully!")

        # Try a simple operation
        print("\n🔄 Testing Put operation...")
        await client.put("test-key", {"msg": "TLS works!"})
        print("✅ Put succeeded!")

        print("\n🔄 Testing Get operation...")
        value = await client.get("test-key")
        print(f"✅ Get succeeded! Value: {value}")

    except TimeoutError:
        print("❌ TIMEOUT waiting for client to start")
        print("\n📋 This means the gRPC channel never became READY")
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await client.stop()
        print("\n🛑 Client stopped")


if __name__ == "__main__":
    asyncio.run(main())

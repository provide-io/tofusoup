#!/usr/bin/env python3
"""
Debug script to test Python client → Go server connection.
This will help us see if the SSL override code is being executed.
"""
import asyncio
import sys
from pathlib import Path

# Add debugging to see what's happening
print("=" * 80, file=sys.stderr)
print("DEBUG SCRIPT STARTED", file=sys.stderr)
print("=" * 80, file=sys.stderr)

from tofusoup.rpc.client import KVClient

# Find soup-go
soup_go_candidates = [
    Path("bin/soup-go"),
    Path("harnesses/bin/soup-go"),
]
soup_go_path = None
for candidate in soup_go_candidates:
    if candidate.exists():
        soup_go_path = str(candidate.resolve())
        break

if not soup_go_path:
    print("ERROR: soup-go not found!", file=sys.stderr)
    sys.exit(1)

print(f"Using soup-go: {soup_go_path}", file=sys.stderr)


async def main():
    """Test Python client → Go server connection."""
    print("\nCreating KVClient...", file=sys.stderr)

    client = KVClient(
        server_path=soup_go_path,
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="secp256r1"
    )

    print("Starting client...", file=sys.stderr)
    try:
        await asyncio.wait_for(client.start(), timeout=15.0)
        print("✅ Client started successfully!", file=sys.stderr)

        # Test operations
        await client.put("test-key", b"test-value")
        result = await client.get("test-key")
        print(f"✅ Put/Get succeeded: {result}", file=sys.stderr)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        try:
            await client.close()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())

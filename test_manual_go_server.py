#!/usr/bin/env python3
"""Manual verification script for Go server RPC functionality.

Tests:
1. Go server starts and accepts connections
2. Put stores raw JSON
3. Get returns enriched JSON with combo metadata
4. Storage files contain raw JSON (not enriched)
"""

import asyncio
import json
from pathlib import Path
import subprocess
import sys
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tofusoup.common.utils import get_cache_dir


async def test_go_server_manual():
    """Manual test of Go server with direct subprocess calls."""

    # Find soup-go binary
    soup_go_path = get_cache_dir() / "harnesses" / "soup-go"
    if not soup_go_path.exists():
        print(f"❌ soup-go binary not found at {soup_go_path}")
        print("   Run: soup harness build soup-go")
        return False

    print(f"✓ Found soup-go at: {soup_go_path}")

    # Create test directory
    test_dir = Path("/tmp/manual_go_server_test")
    test_dir.mkdir(exist_ok=True)
    storage_dir = test_dir / "kv-store"
    storage_dir.mkdir(exist_ok=True)

    print(f"✓ Test directory: {test_dir}")
    print(f"✓ Storage directory: {storage_dir}")

    # Start Go server
    port = 50099
    print(f"\n🚀 Starting Go server on port {port}...")

    server_env = {
        **subprocess.os.environ.copy(),
        "KV_STORAGE_DIR": str(storage_dir),
        "SERVER_LANGUAGE": "go",
        "CLIENT_LANGUAGE": "python",
        "COMBO_ID": "manual_test_python_to_go",
        "TLS_MODE": "disabled",
        "TLS_KEY_TYPE": "ec",
        "TLS_KEY_SIZE": "256",
        "TLS_CURVE": "secp256r1",
    }

    server_proc = subprocess.Popen(
        [str(soup_go_path), "rpc", "kv", "server", "--port", str(port), "--tls-mode", "disabled"],
        env=server_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for server to start
    await asyncio.sleep(2)

    if server_proc.poll() is not None:
        stdout, stderr = server_proc.communicate()
        print(f"❌ Server failed to start")
        print(f"   stdout: {stdout}")
        print(f"   stderr: {stderr}")
        return False

    print(f"✓ Server started (PID: {server_proc.pid})")

    try:
        # Test 1: Put raw JSON using soup-go client
        print(f"\n📤 Test 1: Put raw JSON...")
        test_key = "manual_test_key"
        test_value = json.dumps({
            "test": "manual_verification",
            "client": "go_cli",
            "iteration": 1
        })

        put_result = subprocess.run(
            [
                str(soup_go_path), "rpc", "kv", "put",
                test_key, test_value,
                f"--address=127.0.0.1:{port}",
            ],
            capture_output=True,
            text=True,
        )

        if put_result.returncode != 0:
            print(f"❌ Put failed: {put_result.stderr}")
            return False

        print(f"✓ Put succeeded")

        # Test 2: Verify stored file contains raw JSON (no enrichment)
        print(f"\n📂 Test 2: Check stored file...")
        stored_file = storage_dir / f"kv-data-{test_key}"

        if not stored_file.exists():
            print(f"❌ Stored file not found: {stored_file}")
            return False

        with stored_file.open("r") as f:
            stored_data = json.load(f)

        print(f"✓ Stored file found")
        print(f"   Stored data: {json.dumps(stored_data, indent=2)}")

        if "server_handshake" in stored_data:
            print(f"❌ Stored file should NOT contain server_handshake (enrichment should be on Get)")
            print(f"   Found: {list(stored_data.keys())}")
            return False

        print(f"✓ Stored file contains raw JSON (no server_handshake)")

        # Test 3: Get enriched JSON using soup-go client
        print(f"\n📥 Test 3: Get enriched JSON...")

        get_result = subprocess.run(
            [
                str(soup_go_path), "rpc", "kv", "get",
                test_key,
                f"--address=127.0.0.1:{port}",
            ],
            capture_output=True,
            text=True,
        )

        if get_result.returncode != 0:
            print(f"❌ Get failed: {get_result.stderr}")
            return False

        print(f"✓ Get succeeded")

        # Parse the retrieved value
        retrieved_data = json.loads(get_result.stdout.strip())
        print(f"   Retrieved data keys: {list(retrieved_data.keys())}")

        # Test 4: Verify enrichment
        print(f"\n🔍 Test 4: Verify enrichment metadata...")

        if "server_handshake" not in retrieved_data:
            print(f"❌ Retrieved value should contain server_handshake")
            print(f"   Keys found: {list(retrieved_data.keys())}")
            return False

        print(f"✓ server_handshake present")

        handshake = retrieved_data["server_handshake"]
        print(f"   server_handshake: {json.dumps(handshake, indent=2)}")

        # Verify combo identification
        checks = [
            ("server_language", "go"),
            ("client_language", "python"),
            ("combo_id", "manual_test_python_to_go"),
        ]

        for field, expected in checks:
            if field not in handshake:
                print(f"❌ Missing field: {field}")
                return False
            if handshake[field] != expected:
                print(f"❌ {field}: expected '{expected}', got '{handshake[field]}'")
                return False
            print(f"✓ {field} = {handshake[field]}")

        # Verify crypto_config
        if "crypto_config" in handshake:
            crypto = handshake["crypto_config"]
            print(f"✓ crypto_config present: {crypto}")
            if crypto.get("key_type") != "ec":
                print(f"❌ Expected key_type='ec', got '{crypto.get('key_type')}'")
                return False
            # Note: curve may be "auto" (client auto-detect) or specific curve name
            curve = crypto.get("curve")
            if curve not in ["auto", "secp256r1", "secp384r1", "secp521r1"]:
                print(f"❌ Invalid curve value: '{curve}'")
                return False
            print(f"✓ Crypto config correct (curve={curve})")

        print(f"\n✅ All tests passed!")
        return True

    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        print(f"✓ Server stopped")


if __name__ == "__main__":
    success = asyncio.run(test_go_server_manual())
    sys.exit(0 if success else 1)

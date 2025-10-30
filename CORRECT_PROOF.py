#!/usr/bin/env python3
"""CORRECT PROOF: All combinations use SAME storage dir, different KEYS."""

import asyncio
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, "src")

from tofusoup.common.utils import get_cache_dir


# ONE shared storage directory for ALL combinations
SHARED_STORAGE = Path("/tmp/PROOF_SHARED_STORAGE")
SHARED_STORAGE.mkdir(exist_ok=True)


async def test_go_to_go():
    """Test Go → Go with shared storage."""
    print("\n" + "="*60)
    print("TEST 1: Go Client → Go Server")
    print("="*60)

    soup_go = get_cache_dir() / "harnesses" / "soup-go"

    # Start Go server (shared storage)
    env = {
        **subprocess.os.environ.copy(),
        "KV_STORAGE_DIR": str(SHARED_STORAGE),
        "SERVER_LANGUAGE": "go",
        "CLIENT_LANGUAGE": "go",
        "COMBO_ID": "go_to_go",
    }

    server_proc = subprocess.Popen(
        [str(soup_go), "rpc", "kv", "server", "--port", "50092", "--tls-mode", "disabled"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    await asyncio.sleep(2)

    # UNIQUE KEY per combo
    test_key = "combo_go_to_go"
    test_value = json.dumps({"original": "go_to_go"})

    # Put
    subprocess.run(
        [str(soup_go), "rpc", "kv", "put", test_key, test_value, "--address=127.0.0.1:50092"],
        capture_output=True,
    )

    # Get
    result = subprocess.run(
        [str(soup_go), "rpc", "kv", "get", test_key, "--address=127.0.0.1:50092"],
        capture_output=True,
        text=True,
    )

    retrieved = json.loads(result.stdout)

    server_proc.terminate()
    server_proc.wait(timeout=5)

    return test_key, retrieved


async def test_go_to_python():
    """Test Go → Python with shared storage."""
    print("\n" + "="*60)
    print("TEST 2: Go Client → Python Server")
    print("="*60)

    soup_go = get_cache_dir() / "harnesses" / "soup-go"
    server_script = Path.cwd() / "src" / "tofusoup" / "rpc" / "server.py"

    # Start Python server (shared storage)
    env = {
        **subprocess.os.environ.copy(),
        "PLUGIN_MAGIC_COOKIE_KEY": "BASIC_PLUGIN",
        "BASIC_PLUGIN": "hello",
        "PLUGIN_PROTOCOL_VERSIONS": "1",
        "KV_STORAGE_DIR": str(SHARED_STORAGE),
        "SERVER_LANGUAGE": "python",
        "CLIENT_LANGUAGE": "go",
        "COMBO_ID": "go_to_python",
    }

    server_proc = subprocess.Popen(
        ["python3", str(server_script)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    await asyncio.sleep(2)

    # Get handshake
    handshake = server_proc.stdout.readline().strip()
    address = handshake.split("|")[3]

    # UNIQUE KEY per combo
    test_key = "combo_go_to_python"
    test_value = json.dumps({"original": "go_to_python"})

    # Put
    subprocess.run(
        [str(soup_go), "rpc", "kv", "put", test_key, test_value, f"--address={address}"],
        capture_output=True,
    )

    # Get
    result = subprocess.run(
        [str(soup_go), "rpc", "kv", "get", test_key, f"--address={address}"],
        capture_output=True,
        text=True,
    )

    retrieved = json.loads(result.stdout)

    server_proc.terminate()
    server_proc.wait(timeout=5)

    return test_key, retrieved


async def test_python_to_python():
    """Test Python → Python with shared storage."""
    print("\n" + "="*60)
    print("TEST 3: Python Client → Python Server")
    print("="*60)

    from tofusoup.rpc.client import KVClient

    server_script = Path.cwd() / "src" / "tofusoup" / "rpc" / "server.py"

    # Create client (shared storage)
    client = KVClient(server_path=str(server_script), tls_mode="disabled")
    client.subprocess_env["KV_STORAGE_DIR"] = str(SHARED_STORAGE)
    client.subprocess_env["SERVER_LANGUAGE"] = "python"
    client.subprocess_env["CLIENT_LANGUAGE"] = "python"
    client.subprocess_env["COMBO_ID"] = "python_to_python"

    await client.start()

    # UNIQUE KEY per combo
    test_key = "combo_python_to_python"
    test_value = json.dumps({"original": "python_to_python"}).encode()

    # Put
    await client.put(test_key, test_value)

    # Get
    retrieved_bytes = await client.get(test_key)
    retrieved = json.loads(retrieved_bytes.decode())

    await client.close()

    return test_key, retrieved


async def main():
    """Run all tests with SHARED storage."""
    print("\n" + "="*60)
    print("CORRECT PROOF: Shared Storage, Different Keys")
    print("="*60)
    print(f"\nShared storage directory: {SHARED_STORAGE}")

    results = {}

    # Run all tests
    key1, data1 = await test_go_to_go()
    results[key1] = data1

    key2, data2 = await test_go_to_python()
    results[key2] = data2

    key3, data3 = await test_python_to_python()
    results[key3] = data3

    # Show results
    print("\n" + "="*60)
    print("PROOF: ALL IN ONE DIRECTORY")
    print("="*60)

    print(f"\nStorage directory: {SHARED_STORAGE}")
    print(f"\nFiles created:")

    for key in results.keys():
        storage_file = SHARED_STORAGE / f"kv-data-{key}"
        if storage_file.exists():
            print(f"  ✓ kv-data-{key}")

    print(f"\n" + "="*60)
    print("STORAGE FILES (raw JSON, no enrichment):")
    print("="*60)

    for key in results.keys():
        storage_file = SHARED_STORAGE / f"kv-data-{key}"
        if storage_file.exists():
            with storage_file.open() as f:
                stored = json.load(f)
            print(f"\n{key}:")
            print(f"  Stored: {json.dumps(stored)}")
            print(f"  Has server_handshake: {'server_handshake' in stored}")

    print(f"\n" + "="*60)
    print("RETRIEVED DATA (enriched JSON with combo metadata):")
    print("="*60)

    for key, data in results.items():
        print(f"\n{key}:")
        print(f"  Has server_handshake: {'server_handshake' in data}")
        if 'server_handshake' in data:
            sh = data['server_handshake']
            print(f"  server_language: {sh.get('server_language')}")
            print(f"  client_language: {sh.get('client_language')}")
            print(f"  combo_id: {sh.get('combo_id')}")

    print(f"\n" + "="*60)
    print("VERIFY:")
    print("="*60)
    print(f"ls -la {SHARED_STORAGE}/")
    print(f"cat {SHARED_STORAGE}/kv-data-*")


if __name__ == "__main__":
    asyncio.run(main())

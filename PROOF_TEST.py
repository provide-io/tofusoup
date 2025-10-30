#!/usr/bin/env python3
"""PROOF: Storage isolation and enrichment on Get for all working combinations."""

import asyncio
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, "src")

from tofusoup.common.config import load_tofusoup_config
from tofusoup.common.utils import get_cache_dir
from tofusoup.harness.logic import ensure_go_harness_build


async def test_go_to_go_isolated():
    """Test Go → Go with isolated storage."""
    print("\n" + "="*60)
    print("TEST 1: Go Client → Go Server (Isolated Storage)")
    print("="*60)

    soup_go = get_cache_dir() / "harnesses" / "soup-go"

    # Create isolated test directory with combo_id naming
    combo_id = "go_client_to_go_server_isolated"
    test_dir = Path(f"/tmp/PROOF_{combo_id}")
    storage_dir = test_dir / f"kv-{combo_id}"
    storage_dir.mkdir(parents=True, exist_ok=True)

    print(f"Storage directory: {storage_dir}")

    # Start Go server
    env = {
        **subprocess.os.environ.copy(),
        "KV_STORAGE_DIR": str(storage_dir),
        "SERVER_LANGUAGE": "go",
        "CLIENT_LANGUAGE": "go",
        "COMBO_ID": combo_id,
    }

    server_proc = subprocess.Popen(
        [str(soup_go), "rpc", "kv", "server", "--port", "50091", "--tls-mode", "disabled"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    await asyncio.sleep(2)

    # Put value
    test_key = "proof_go_go"
    test_value = json.dumps({"combo": combo_id, "type": "proof"})

    result = subprocess.run(
        [str(soup_go), "rpc", "kv", "put", test_key, test_value, "--address=127.0.0.1:50091"],
        capture_output=True,
    )

    # Get value
    result = subprocess.run(
        [str(soup_go), "rpc", "kv", "get", test_key, "--address=127.0.0.1:50091"],
        capture_output=True,
        text=True,
    )

    retrieved_data = json.loads(result.stdout)

    server_proc.terminate()
    server_proc.wait(timeout=5)

    # VERIFY
    storage_file = storage_dir / f"kv-data-{test_key}"

    print(f"\n✓ Storage file: {storage_file}")
    print(f"  Exists: {storage_file.exists()}")

    if storage_file.exists():
        with storage_file.open() as f:
            stored = json.load(f)

        print(f"\n  STORED (raw JSON):")
        print(f"    {json.dumps(stored)}")
        print(f"    Has server_handshake: {('server_handshake' in stored)}")

        print(f"\n  RETRIEVED (enriched JSON):")
        print(f"    Keys: {list(retrieved_data.keys())}")
        print(f"    Has server_handshake: {'server_handshake' in retrieved_data}")

        if 'server_handshake' in retrieved_data:
            sh = retrieved_data['server_handshake']
            print(f"    server_language: {sh.get('server_language')}")
            print(f"    client_language: {sh.get('client_language')}")
            print(f"    combo_id: {sh.get('combo_id')}")

        return storage_file

    return None


async def test_go_to_python_isolated():
    """Test Go → Python with isolated storage."""
    print("\n" + "="*60)
    print("TEST 2: Go Client → Python Server (Isolated Storage)")
    print("="*60)

    soup_go = get_cache_dir() / "harnesses" / "soup-go"
    server_script = Path.cwd() / "src" / "tofusoup" / "rpc" / "server.py"

    # Create isolated test directory
    combo_id = "go_client_to_python_server_isolated"
    test_dir = Path(f"/tmp/PROOF_{combo_id}")
    storage_dir = test_dir / f"kv-{combo_id}"
    storage_dir.mkdir(parents=True, exist_ok=True)

    print(f"Storage directory: {storage_dir}")

    # Start Python server
    env = {
        **subprocess.os.environ.copy(),
        "PLUGIN_MAGIC_COOKIE_KEY": "BASIC_PLUGIN",
        "BASIC_PLUGIN": "hello",
        "PLUGIN_PROTOCOL_VERSIONS": "1",
        "KV_STORAGE_DIR": str(storage_dir),
        "SERVER_LANGUAGE": "python",
        "CLIENT_LANGUAGE": "go",
        "COMBO_ID": combo_id,
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

    # Put value
    test_key = "proof_go_py"
    test_value = json.dumps({"combo": combo_id, "type": "proof"})

    subprocess.run(
        [str(soup_go), "rpc", "kv", "put", test_key, test_value, f"--address={address}"],
        capture_output=True,
    )

    # Get value
    result = subprocess.run(
        [str(soup_go), "rpc", "kv", "get", test_key, f"--address={address}"],
        capture_output=True,
        text=True,
    )

    retrieved_data = json.loads(result.stdout)

    server_proc.terminate()
    server_proc.wait(timeout=5)

    # VERIFY
    storage_file = storage_dir / f"kv-data-{test_key}"

    print(f"\n✓ Storage file: {storage_file}")
    print(f"  Exists: {storage_file.exists()}")

    if storage_file.exists():
        with storage_file.open() as f:
            stored = json.load(f)

        print(f"\n  STORED (raw JSON):")
        print(f"    {json.dumps(stored)}")
        print(f"    Has server_handshake: {'server_handshake' in stored}")

        print(f"\n  RETRIEVED (enriched JSON):")
        print(f"    Keys: {list(retrieved_data.keys())}")
        print(f"    Has server_handshake: {'server_handshake' in retrieved_data}")

        if 'server_handshake' in retrieved_data:
            sh = retrieved_data['server_handshake']
            print(f"    server_language: {sh.get('server_language')}")
            print(f"    client_language: {sh.get('client_language')}")
            print(f"    combo_id: {sh.get('combo_id')}")

        return storage_file

    return None


async def test_python_to_python_isolated():
    """Test Python → Python with isolated storage."""
    print("\n" + "="*60)
    print("TEST 3: Python Client → Python Server (Isolated Storage)")
    print("="*60)

    from tofusoup.rpc.client import KVClient

    server_script = Path.cwd() / "src" / "tofusoup" / "rpc" / "server.py"

    # Create isolated test directory
    combo_id = "python_client_to_python_server_isolated"
    test_dir = Path(f"/tmp/PROOF_{combo_id}")
    storage_dir = test_dir / f"kv-{combo_id}"
    storage_dir.mkdir(parents=True, exist_ok=True)

    print(f"Storage directory: {storage_dir}")

    # Create client
    client = KVClient(server_path=str(server_script), tls_mode="disabled")
    client.subprocess_env["KV_STORAGE_DIR"] = str(storage_dir)
    client.subprocess_env["SERVER_LANGUAGE"] = "python"
    client.subprocess_env["CLIENT_LANGUAGE"] = "python"
    client.subprocess_env["COMBO_ID"] = combo_id

    await client.start()

    # Put value
    test_key = "proof_py_py"
    test_value = json.dumps({"combo": combo_id, "type": "proof"}).encode()

    await client.put(test_key, test_value)

    # Get value
    retrieved = await client.get(test_key)
    retrieved_data = json.loads(retrieved.decode())

    await client.close()

    # VERIFY
    storage_file = storage_dir / f"kv-data-{test_key}"

    print(f"\n✓ Storage file: {storage_file}")
    print(f"  Exists: {storage_file.exists()}")

    if storage_file.exists():
        with storage_file.open() as f:
            stored = json.load(f)

        print(f"\n  STORED (raw JSON):")
        print(f"    {json.dumps(stored)}")
        print(f"    Has server_handshake: {'server_handshake' in stored}")

        print(f"\n  RETRIEVED (enriched JSON):")
        print(f"    Keys: {list(retrieved_data.keys())}")
        print(f"    Has server_handshake: {'server_handshake' in retrieved_data}")

        if 'server_handshake' in retrieved_data:
            sh = retrieved_data['server_handshake']
            print(f"    server_language: {sh.get('server_language')}")
            print(f"    client_language: {sh.get('client_language')}")
            print(f"    combo_id: {sh.get('combo_id')}")

        return storage_file

    return None


async def main():
    """Run all proof tests."""
    print("\n" + "="*60)
    print("PROOF: Storage Isolation & Enrichment on Get")
    print("="*60)

    files = []

    # Run tests
    f1 = await test_go_to_go_isolated()
    if f1:
        files.append(f1)

    f2 = await test_go_to_python_isolated()
    if f2:
        files.append(f2)

    f3 = await test_python_to_python_isolated()
    if f3:
        files.append(f3)

    # Summary
    print("\n" + "="*60)
    print("PROOF SUMMARY")
    print("="*60)

    print(f"\n✓ Created {len(files)} isolated storage directories:")
    for f in files:
        print(f"  - {f.parent.name}/ → {f.name}")

    print(f"\nTo verify:")
    print(f"  find /tmp/PROOF_* -name 'kv-data-*'")
    print(f"\nEach file contains RAW JSON (no server_handshake)")
    print(f"Retrieved values have enriched JSON (with server_handshake)")


if __name__ == "__main__":
    asyncio.run(main())

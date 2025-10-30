#!/usr/bin/env python3
"""Test actual RPC combinations to see which work."""

import asyncio
import json
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tofusoup.common.config import load_tofusoup_config
from tofusoup.harness.logic import ensure_go_harness_build
from tofusoup.rpc.client import KVClient


async def test_python_client_to_go_server():
    """Test Python client → Go server (the simple matrix test)."""
    print("\n" + "="*60)
    print("Testing: Python Client → Go Server")
    print("="*60)

    project_root = Path.cwd()
    test_dir = Path("/tmp/combo_test_pyclient_goserver")
    test_dir.mkdir(exist_ok=True)

    try:
        config = load_tofusoup_config(project_root)
        go_server_path = ensure_go_harness_build("soup-go", project_root, config)
        print(f"✓ Go server binary: {go_server_path}")

        # Create client
        client = KVClient(server_path=str(go_server_path), tls_mode="disabled")
        client.subprocess_env["KV_STORAGE_DIR"] = str(test_dir)
        client.subprocess_env["SERVER_LANGUAGE"] = "go"
        client.subprocess_env["CLIENT_LANGUAGE"] = "python"
        client.subprocess_env["COMBO_ID"] = "pyclient_goserver_test"

        test_key = f"test_{uuid.uuid4().hex[:8]}"
        test_value = json.dumps({
            "combo": "python_client_to_go_server",
            "test_key": test_key
        }).encode()

        print(f"✓ Starting client...")
        await client.start()
        print(f"✓ Client started")

        print(f"✓ Putting value for key: {test_key}")
        await client.put(test_key, test_value)

        print(f"✓ Getting value...")
        retrieved = await client.get(test_key)

        data = json.loads(retrieved.decode())
        print(f"✓ Retrieved data keys: {list(data.keys())}")

        # Check storage
        storage_file = test_dir / f"kv-data-{test_key}"
        if storage_file.exists():
            with storage_file.open("r") as f:
                stored = json.load(f)
            has_handshake_in_storage = "server_handshake" in stored
            print(f"✓ Storage file exists: {storage_file}")
            print(f"  - Contains server_handshake: {has_handshake_in_storage}")
        else:
            print(f"⚠️  Storage file not found: {storage_file}")

        # Check enrichment
        if "server_handshake" in data:
            handshake = data["server_handshake"]
            print(f"✓ Enrichment present:")
            print(f"  - server_language: {handshake.get('server_language')}")
            print(f"  - client_language: {handshake.get('client_language')}")
            print(f"  - combo_id: {handshake.get('combo_id')}")
        else:
            print(f"❌ No server_handshake in retrieved data")

        await client.close()
        print(f"\n✅ Python Client → Go Server: WORKS")
        return True

    except Exception as e:
        print(f"\n❌ Python Client → Go Server: FAILED")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_go_client_to_go_server():
    """Test Go client → Go server using soup-go CLI."""
    print("\n" + "="*60)
    print("Testing: Go Client → Go Server")
    print("="*60)

    import subprocess
    from tofusoup.common.utils import get_cache_dir

    soup_go = get_cache_dir() / "harnesses" / "soup-go"
    if not soup_go.exists():
        print(f"❌ soup-go not found at {soup_go}")
        return False

    print(f"✓ soup-go binary: {soup_go}")

    test_dir = Path("/tmp/combo_test_goclient_goserver")
    test_dir.mkdir(exist_ok=True)

    try:
        # Start server
        port = 50098
        env = {
            **subprocess.os.environ.copy(),
            "KV_STORAGE_DIR": str(test_dir),
            "SERVER_LANGUAGE": "go",
            "CLIENT_LANGUAGE": "go",
            "COMBO_ID": "goclient_goserver_test",
        }

        print(f"✓ Starting Go server on port {port}...")
        server = subprocess.Popen(
            [str(soup_go), "rpc", "kv", "server", "--port", str(port), "--tls-mode", "disabled"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        await asyncio.sleep(2)

        if server.poll() is not None:
            print(f"❌ Server failed to start")
            return False

        print(f"✓ Server started")

        # Test with Go client
        test_key = f"test_{uuid.uuid4().hex[:8]}"
        test_value = json.dumps({"combo": "go_client_to_go_server", "test_key": test_key})

        print(f"✓ Putting value with Go client...")
        put_result = subprocess.run(
            [str(soup_go), "rpc", "kv", "put", test_key, test_value, f"--address=127.0.0.1:{port}"],
            capture_output=True,
            text=True,
        )

        if put_result.returncode != 0:
            print(f"❌ Put failed: {put_result.stderr}")
            server.terminate()
            return False

        print(f"✓ Put succeeded")

        # Get value
        print(f"✓ Getting value with Go client...")
        get_result = subprocess.run(
            [str(soup_go), "rpc", "kv", "get", test_key, f"--address=127.0.0.1:{port}"],
            capture_output=True,
            text=True,
        )

        if get_result.returncode != 0:
            print(f"❌ Get failed: {get_result.stderr}")
            server.terminate()
            return False

        print(f"✓ Get succeeded")

        data = json.loads(get_result.stdout.strip())
        print(f"✓ Retrieved data keys: {list(data.keys())}")

        # Check storage
        storage_file = test_dir / f"kv-data-{test_key}"
        if storage_file.exists():
            with storage_file.open("r") as f:
                stored = json.load(f)
            has_handshake_in_storage = "server_handshake" in stored
            print(f"✓ Storage file exists: {storage_file}")
            print(f"  - Contains server_handshake: {has_handshake_in_storage}")
        else:
            print(f"⚠️  Storage file not found: {storage_file}")

        # Check enrichment
        if "server_handshake" in data:
            handshake = data["server_handshake"]
            print(f"✓ Enrichment present:")
            print(f"  - server_language: {handshake.get('server_language')}")
            print(f"  - client_language: {handshake.get('client_language')}")
            print(f"  - combo_id: {handshake.get('combo_id')}")
        else:
            print(f"❌ No server_handshake in retrieved data")

        server.terminate()
        server.wait(timeout=5)
        print(f"\n✅ Go Client → Go Server: WORKS")
        return True

    except Exception as e:
        print(f"\n❌ Go Client → Go Server: FAILED")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            server.terminate()
        except:
            pass
        return False


async def main():
    """Run all combination tests."""
    print("\n" + "="*60)
    print("RPC COMBINATION TESTING")
    print("="*60)

    results = {}

    # Test 1: Go Client → Go Server
    results["go_client_to_go_server"] = await test_go_client_to_go_server()

    # Test 2: Python Client → Go Server
    results["python_client_to_go_server"] = await test_python_client_to_go_server()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for combo, success in results.items():
        status = "✅ WORKS" if success else "❌ FAILED"
        print(f"{combo:40s} {status}")

    print("\n" + "="*60)
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"Result: {passed}/{total} combinations working")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

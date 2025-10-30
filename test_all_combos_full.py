#!/usr/bin/env python3
"""Test all RPC combinations with multiple crypto configs."""

import asyncio
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tofusoup.common.config import load_tofusoup_config
from tofusoup.common.utils import get_cache_dir
from tofusoup.harness.logic import ensure_go_harness_build
from tofusoup.rpc.client import KVClient


# Crypto configurations to test
CRYPTO_CONFIGS = [
    {"name": "disabled", "tls_mode": "disabled", "key_type": None, "curve": None},
    {"name": "ec_p256", "tls_mode": "auto", "key_type": "ec", "curve": "secp256r1"},
    {"name": "ec_p384", "tls_mode": "auto", "key_type": "ec", "curve": "secp384r1"},
    {"name": "ec_p521", "tls_mode": "auto", "key_type": "ec", "curve": "secp521r1"},
    {"name": "rsa_2048", "tls_mode": "auto", "key_type": "rsa", "size": 2048},
    {"name": "rsa_4096", "tls_mode": "auto", "key_type": "rsa", "size": 4096},
]


async def test_python_to_python(crypto_config):
    """Test Python client → Python server."""
    combo_name = f"python_to_python_{crypto_config['name']}"
    print(f"\n{'='*60}")
    print(f"Testing: Python → Python ({crypto_config['name']})")
    print(f"{'='*60}")

    test_dir = Path(f"/tmp/test_{combo_name}")
    test_dir.mkdir(exist_ok=True)

    # Start Python server
    server_script = Path.cwd() / "src" / "tofusoup" / "rpc" / "server.py"

    env = {
        **subprocess.os.environ.copy(),
        "KV_STORAGE_DIR": str(test_dir),
        "SERVER_LANGUAGE": "python",
        "CLIENT_LANGUAGE": "python",
        "COMBO_ID": combo_name,
        "TLS_MODE": crypto_config["tls_mode"],
    }

    if crypto_config["key_type"]:
        env["TLS_KEY_TYPE"] = crypto_config["key_type"]
        if "curve" in crypto_config:
            env["TLS_CURVE"] = crypto_config["curve"]
        if "size" in crypto_config:
            env["TLS_KEY_SIZE"] = str(crypto_config["size"])

    print(f"Starting Python server with {crypto_config['name']}...")
    server_proc = subprocess.Popen(
        ["python3", str(server_script)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for handshake
    await asyncio.sleep(2)

    if server_proc.poll() is not None:
        stdout, stderr = server_proc.communicate()
        print(f"❌ Server failed to start")
        print(f"   stdout: {stdout[:200]}")
        print(f"   stderr: {stderr[:200]}")
        return False

    # Get handshake from stdout
    try:
        handshake_line = server_proc.stdout.readline().strip()
        print(f"  Handshake: {handshake_line[:60]}...")

        # Parse address from handshake
        parts = handshake_line.split("|")
        if len(parts) >= 5:
            server_addr = parts[3]
            print(f"  Server address: {server_addr}")
        else:
            print(f"❌ Invalid handshake format")
            server_proc.terminate()
            return False

    except Exception as e:
        print(f"❌ Failed to get handshake: {e}")
        server_proc.terminate()
        return False

    try:
        # Create Python client
        print(f"  Creating Python client...")
        client = KVClient(
            server_path=str(server_script),
            tls_mode=crypto_config["tls_mode"],
            tls_key_type=crypto_config.get("key_type"),
        )
        client.subprocess_env["KV_STORAGE_DIR"] = str(test_dir)

        test_key = f"test_{crypto_config['name']}"
        test_value = json.dumps({
            "combo": combo_name,
            "crypto": crypto_config["name"],
        }).encode()

        print(f"  Starting client...")
        await asyncio.wait_for(client.start(), timeout=10)

        print(f"  Putting value...")
        await client.put(test_key, test_value)

        print(f"  Getting value...")
        retrieved = await client.get(test_key)

        data = json.loads(retrieved.decode())

        # Check storage
        storage_file = test_dir / f"kv-data-{test_key}"
        if storage_file.exists():
            with storage_file.open("r") as f:
                stored = json.load(f)
            has_handshake = "server_handshake" in stored
            print(f"✓ Storage file: raw JSON (handshake in storage: {has_handshake})")

        # Check enrichment
        if "server_handshake" in data:
            sh = data["server_handshake"]
            print(f"✓ Enrichment present:")
            print(f"  - server_language: {sh.get('server_language')}")
            print(f"  - client_language: {sh.get('client_language')}")
            print(f"  - combo_id: {sh.get('combo_id')}")
            success = True
        else:
            print(f"❌ No enrichment in retrieved data")
            success = False

        await client.close()
        server_proc.terminate()
        server_proc.wait(timeout=5)

        if success:
            print(f"✅ Python → Python ({crypto_config['name']}): WORKS")
        return success

    except asyncio.TimeoutError:
        print(f"❌ Client start timeout")
        server_proc.terminate()
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        server_proc.terminate()
        return False


def test_go_to_go_crypto(crypto_config):
    """Test Go client → Go server with specific crypto config."""
    combo_name = f"go_to_go_{crypto_config['name']}"
    print(f"\n{'='*60}")
    print(f"Testing: Go → Go ({crypto_config['name']})")
    print(f"{'='*60}")

    soup_go = get_cache_dir() / "harnesses" / "soup-go"
    test_dir = Path(f"/tmp/test_{combo_name}")
    test_dir.mkdir(exist_ok=True)

    # Build server args
    server_args = [str(soup_go), "rpc", "kv", "server", "--port", "50090"]
    if crypto_config["tls_mode"] == "disabled":
        server_args.append("--tls-mode=disabled")
    else:
        server_args.extend([
            "--tls-mode=auto",
            f"--tls-key-type={crypto_config['key_type']}",
        ])
        if "curve" in crypto_config:
            server_args.append(f"--tls-curve={crypto_config['curve']}")

    env = {
        **subprocess.os.environ.copy(),
        "KV_STORAGE_DIR": str(test_dir),
        "SERVER_LANGUAGE": "go",
        "CLIENT_LANGUAGE": "go",
        "COMBO_ID": combo_name,
        "TLS_MODE": crypto_config["tls_mode"],
    }

    if crypto_config.get("key_type"):
        env["TLS_KEY_TYPE"] = crypto_config["key_type"]
        if "curve" in crypto_config:
            env["TLS_CURVE"] = crypto_config["curve"]
        if "size" in crypto_config:
            env["TLS_KEY_SIZE"] = str(crypto_config["size"])

    print(f"Starting Go server...")
    server = subprocess.Popen(server_args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    import time
    time.sleep(2)

    if server.poll() is not None:
        print(f"❌ Server failed to start")
        return False

    try:
        test_key = f"test_{crypto_config['name']}"
        test_value = json.dumps({"combo": combo_name, "crypto": crypto_config["name"]})

        # Put
        result = subprocess.run(
            [str(soup_go), "rpc", "kv", "put", test_key, test_value, "--address=127.0.0.1:50090"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"❌ Put failed: {result.stderr}")
            server.terminate()
            return False

        # Get
        result = subprocess.run(
            [str(soup_go), "rpc", "kv", "get", test_key, "--address=127.0.0.1:50090"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"❌ Get failed")
            server.terminate()
            return False

        data = json.loads(result.stdout)

        # Check storage
        storage_file = test_dir / f"kv-data-{test_key}"
        if storage_file.exists():
            with storage_file.open("r") as f:
                stored = json.load(f)
            has_handshake = "server_handshake" in stored
            print(f"✓ Storage file: raw JSON (handshake: {has_handshake})")

        # Check enrichment
        if "server_handshake" in data:
            sh = data["server_handshake"]
            print(f"✓ Enrichment: server={sh.get('server_language')}, client={sh.get('client_language')}")
            success = True
        else:
            print(f"❌ No enrichment")
            success = False

        server.terminate()
        server.wait(timeout=5)

        if success:
            print(f"✅ Go → Go ({crypto_config['name']}): WORKS")
        return success

    except Exception as e:
        print(f"❌ Error: {e}")
        server.terminate()
        return False


async def main():
    """Run all combination tests."""
    print("\n" + "="*60)
    print("COMPREHENSIVE RPC COMBINATION TESTING")
    print("="*60)

    results = {}

    # Test Go → Go with all crypto configs
    print(f"\n{'='*60}")
    print("GO CLIENT → GO SERVER (all crypto configs)")
    print(f"{'='*60}")
    for crypto in CRYPTO_CONFIGS:
        combo_key = f"go_to_go_{crypto['name']}"
        results[combo_key] = test_go_to_go_crypto(crypto)

    # Test Python → Python with all crypto configs
    print(f"\n{'='*60}")
    print("PYTHON CLIENT → PYTHON SERVER (all crypto configs)")
    print(f"{'='*60}")
    for crypto in CRYPTO_CONFIGS[:1]:  # Start with just disabled TLS
        combo_key = f"python_to_python_{crypto['name']}"
        try:
            results[combo_key] = await asyncio.wait_for(
                test_python_to_python(crypto),
                timeout=30
            )
        except asyncio.TimeoutError:
            print(f"❌ Test timed out")
            results[combo_key] = False

    # Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)

    for combo, success in results.items():
        status = "✅ WORKS" if success else "❌ FAILED"
        print(f"{combo:40s} {status}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nResult: {passed}/{total} combinations working ({passed*100//total}%)")


if __name__ == "__main__":
    asyncio.run(main())

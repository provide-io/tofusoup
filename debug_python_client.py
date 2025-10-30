#!/usr/bin/env python3
"""Low-level debug of Python client connection issues."""

import asyncio
import json
import logging
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Enable verbose logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

from tofusoup.common.config import load_tofusoup_config
from tofusoup.harness.logic import ensure_go_harness_build
from tofusoup.rpc.client import KVClient


async def debug_python_to_go():
    """Debug Python client → Go server connection."""
    print("\n" + "="*60)
    print("DEBUG: Python Client → Go Server")
    print("="*60)

    project_root = Path.cwd()
    test_dir = Path("/tmp/debug_py_to_go")
    test_dir.mkdir(exist_ok=True)

    # Build Go server
    config = load_tofusoup_config(project_root)
    go_server_path = ensure_go_harness_build("soup-go", project_root, config)

    print(f"\n1. Go server path: {go_server_path}")
    print(f"   Exists: {go_server_path.exists()}")

    # Create client
    client = KVClient(
        server_path=str(go_server_path),
        tls_mode="disabled",
    )
    client.connection_timeout = 10  # Override default timeout

    # Set environment
    client.subprocess_env["KV_STORAGE_DIR"] = str(test_dir)
    client.subprocess_env["SERVER_LANGUAGE"] = "go"
    client.subprocess_env["CLIENT_LANGUAGE"] = "python"
    client.subprocess_env["COMBO_ID"] = "debug_py_to_go"
    client.subprocess_env["LOG_LEVEL"] = "DEBUG"

    print(f"\n2. Client configuration:")
    print(f"   server_path: {client.server_path}")
    print(f"   tls_mode: {client.tls_mode}")
    print(f"   connection_timeout: {client.connection_timeout}")
    print(f"   Environment vars: {list(client.subprocess_env.keys())}")

    print(f"\n3. Starting client (this is where it usually hangs)...")
    print(f"   The client will spawn the Go server as subprocess")
    print(f"   and wait for go-plugin handshake on stdout...")

    try:
        # Add timeout to see if it hangs
        await asyncio.wait_for(client.start(), timeout=15)
        print(f"\n✅ Client started successfully!")

        # Try a simple operation
        test_key = "debug_test"
        test_value = b'{"test": "debug"}'

        print(f"\n4. Attempting Put operation...")
        await client.put(test_key, test_value)
        print(f"   ✅ Put succeeded")

        print(f"\n5. Attempting Get operation...")
        retrieved = await client.get(test_key)
        print(f"   ✅ Get succeeded")
        print(f"   Retrieved: {retrieved[:100]}...")

        await client.close()

    except asyncio.TimeoutError:
        print(f"\n❌ TIMEOUT: Client start hung for 15 seconds")
        print(f"\nDEBUG: Checking what subprocess was spawned...")

        if hasattr(client, '_client') and hasattr(client._client, '_process'):
            proc = client._client._process
            if proc:
                print(f"   Process PID: {proc.pid if proc else 'None'}")
                print(f"   Process running: {proc.poll() is None if proc else 'N/A'}")

                # Try to read some output
                if proc and proc.poll() is None:
                    print(f"\n   Checking process stdout/stderr...")
                    # Process is still running but not responding
                    import os
                    import signal

                    print(f"   Sending SIGTERM to process...")
                    try:
                        os.kill(proc.pid, signal.SIGTERM)
                    except:
                        pass

        print(f"\nDEBUG: The issue is that the Go server subprocess")
        print(f"       doesn't output the expected handshake format")
        print(f"       that pyvider-rpcplugin expects.")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


async def debug_python_to_python():
    """Debug Python client → Python server connection."""
    print("\n" + "="*60)
    print("DEBUG: Python Client → Python Server")
    print("="*60)

    test_dir = Path("/tmp/debug_py_to_py")
    test_dir.mkdir(exist_ok=True)

    # Get Python server script
    server_script = Path.cwd() / "src" / "tofusoup" / "rpc" / "server.py"

    print(f"\n1. Python server path: {server_script}")
    print(f"   Exists: {server_script.exists()}")

    # First, manually test if server outputs handshake correctly
    print(f"\n2. Testing server handshake output directly...")

    env = {
        **subprocess.os.environ.copy(),
        "KV_STORAGE_DIR": str(test_dir),
        "SERVER_LANGUAGE": "python",
        "CLIENT_LANGUAGE": "python",
        "COMBO_ID": "debug_py_to_py",
    }

    print(f"   Starting Python server subprocess...")
    server_proc = subprocess.Popen(
        ["python3", str(server_script)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    await asyncio.sleep(2)

    if server_proc.poll() is not None:
        stdout, stderr = server_proc.communicate()
        print(f"   ❌ Server exited immediately")
        print(f"   stdout: {stdout[:200]}")
        print(f"   stderr: {stderr[:200]}")
        return

    # Read handshake
    try:
        handshake_line = server_proc.stdout.readline().strip()
        print(f"   ✅ Server handshake: {handshake_line}")

        # Parse it
        parts = handshake_line.split("|")
        if len(parts) >= 5:
            print(f"   ✅ Handshake format is correct:")
            print(f"      core_version: {parts[0]}")
            print(f"      protocol_version: {parts[1]}")
            print(f"      network: {parts[2]}")
            print(f"      address: {parts[3]}")
            print(f"      protocol: {parts[4]}")

        server_proc.terminate()
        server_proc.wait(timeout=5)

    except Exception as e:
        print(f"   ❌ Failed to read handshake: {e}")
        server_proc.terminate()
        return

    # Now try with Python client
    print(f"\n3. Now testing with Python KVClient...")

    client = KVClient(
        server_path=str(server_script),
        tls_mode="disabled",
    )
    client.connection_timeout = 10  # Override default timeout

    client.subprocess_env["KV_STORAGE_DIR"] = str(test_dir)
    client.subprocess_env["SERVER_LANGUAGE"] = "python"
    client.subprocess_env["CLIENT_LANGUAGE"] = "python"
    client.subprocess_env["COMBO_ID"] = "debug_py_to_py_client"

    print(f"   Starting KVClient...")

    try:
        await asyncio.wait_for(client.start(), timeout=15)
        print(f"   ✅ Client started successfully!")

        # Try operation
        test_key = "debug_test"
        test_value = b'{"test": "debug"}'

        await client.put(test_key, test_value)
        print(f"   ✅ Put succeeded")

        retrieved = await client.get(test_key)
        print(f"   ✅ Get succeeded: {retrieved[:100]}...")

        await client.close()

    except asyncio.TimeoutError:
        print(f"   ❌ TIMEOUT: Client start hung")
        print(f"\n   This suggests the KVClient or pyvider-rpcplugin")
        print(f"   is not correctly handling the server handshake")

    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run debug tests."""
    print("\n" + "="*60)
    print("LOW-LEVEL PYTHON CLIENT DEBUG")
    print("="*60)

    # Test 1: Python → Go
    await debug_python_to_go()

    # Test 2: Python → Python
    await debug_python_to_python()

    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

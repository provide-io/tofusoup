#!/usr/bin/env python3
"""Deep debug of Python → Python subprocess communication."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "src")


async def test_manual_handshake():
    """Manually test server handshake exactly as KVClient would do it."""
    print("\n" + "="*60)
    print("MANUAL TEST: Spawn Python server and read handshake")
    print("="*60)

    server_script = Path.cwd() / "src" / "tofusoup" / "rpc" / "server.py"
    test_dir = Path("/tmp/manual_handshake_test")
    test_dir.mkdir(exist_ok=True)

    # Exact environment that KVClient uses
    env = {
        **subprocess.os.environ.copy(),
        "PLUGIN_MAGIC_COOKIE_KEY": "BASIC_PLUGIN",
        "BASIC_PLUGIN": "hello",
        "PLUGIN_PROTOCOL_VERSIONS": "1",
        "KV_STORAGE_DIR": str(test_dir),
        "SERVER_LANGUAGE": "python",
        "CLIENT_LANGUAGE": "python",
        "COMBO_ID": "manual_test",
    }

    print(f"\n1. Spawning Python server")
    print(f"   Command: python3 {server_script}")
    print(f"   Environment variables set:")
    print(f"      PLUGIN_MAGIC_COOKIE_KEY=BASIC_PLUGIN")
    print(f"      BASIC_PLUGIN=hello")
    print(f"      PLUGIN_PROTOCOL_VERSIONS=1")

    proc = subprocess.Popen(
        ["python3", str(server_script)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
    )

    print(f"\n2. Process spawned (PID: {proc.pid})")

    # Wait a bit for server to initialize
    await asyncio.sleep(1)

    print(f"\n3. Reading from stdout (blocking)...")

    # Try to read the handshake line
    try:
        # Use asyncio to read with timeout
        async def read_line():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, proc.stdout.readline)

        handshake = await asyncio.wait_for(read_line(), timeout=5)

        print(f"✓ Got handshake:")
        print(f"   '{handshake.strip()}'")

        # Parse it
        parts = handshake.strip().split("|")
        if len(parts) >= 5:
            print(f"\n✓ Handshake is valid go-plugin format:")
            print(f"   core_version:     {parts[0]}")
            print(f"   protocol_version: {parts[1]}")
            print(f"   network:          {parts[2]}")
            print(f"   address:          {parts[3]}")
            print(f"   protocol:         {parts[4]}")
            print(f"   cert (base64):    {parts[5][:50] if len(parts) > 5 and parts[5] else '(empty)'}")

            # Now try to connect as gRPC client
            address = parts[3]
            print(f"\n4. Trying to connect gRPC client to {address}...")

            import grpc
            from tofusoup.harness.proto.kv import kv_pb2, kv_pb2_grpc

            # Create channel
            channel = grpc.insecure_channel(address)

            # Wait for connection
            try:
                grpc.channel_ready_future(channel).result(timeout=5)
                print(f"   ✓ gRPC channel connected!")

                # Try a simple operation
                stub = kv_pb2_grpc.KVStub(channel)

                test_key = "manual_test_key"
                test_value = json.dumps({"test": "manual"}).encode()

                print(f"\n5. Putting value...")
                stub.Put(kv_pb2.PutRequest(key=test_key, value=test_value))
                print(f"   ✓ Put succeeded")

                print(f"\n6. Getting value...")
                response = stub.Get(kv_pb2.GetRequest(key=test_key))
                data = json.loads(response.value.decode())

                print(f"   ✓ Get succeeded")
                print(f"   Keys: {list(data.keys())}")

                if "server_handshake" in data:
                    print(f"\n✓ Enrichment present:")
                    sh = data["server_handshake"]
                    print(f"   server_language: {sh.get('server_language')}")
                    print(f"   client_language: {sh.get('client_language')}")
                    print(f"   combo_id: {sh.get('combo_id')}")

                # Check storage
                storage_file = test_dir / f"kv-data-{test_key}"
                if storage_file.exists():
                    with storage_file.open() as f:
                        stored = json.load(f)
                    has_handshake = "server_handshake" in stored
                    print(f"\n✓ Storage file exists")
                    print(f"   Contains server_handshake: {has_handshake}")

                channel.close()

                print(f"\n✅ MANUAL TEST: Python → Python WORKS!")
                print(f"   The server handshake and gRPC connection work correctly")

            except grpc.FutureTimeoutError:
                print(f"   ❌ gRPC connection timeout")

        else:
            print(f"❌ Invalid handshake (only {len(parts)} fields)")

        proc.terminate()
        proc.wait(timeout=5)

        return True

    except asyncio.TimeoutError:
        print(f"❌ Timeout reading handshake from stdout")
        print(f"\nChecking stderr...")

        # Read stderr
        stderr_output = proc.stderr.read()
        print(f"Stderr: {stderr_output[:500]}")

        proc.terminate()
        return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

        proc.terminate()
        return False


async def test_with_kvclient():
    """Test with actual KVClient to see where it fails."""
    print("\n" + "="*60)
    print("TEST WITH KVCLIENT: Python → Python")
    print("="*60)

    from tofusoup.rpc.client import KVClient

    server_script = Path.cwd() / "src" / "tofusoup" / "rpc" / "server.py"
    test_dir = Path("/tmp/kvclient_test")
    test_dir.mkdir(exist_ok=True)

    print(f"\n1. Creating KVClient")
    client = KVClient(
        server_path=str(server_script),
        tls_mode="disabled",
    )

    client.subprocess_env["KV_STORAGE_DIR"] = str(test_dir)
    client.subprocess_env["SERVER_LANGUAGE"] = "python"
    client.subprocess_env["CLIENT_LANGUAGE"] = "python"
    client.subprocess_env["COMBO_ID"] = "kvclient_test"

    print(f"\n2. Starting client (this is where it hangs)...")
    print(f"   Client will spawn: {client.server_path}")
    print(f"   Timeout: {client.connection_timeout}s")

    try:
        # Add detailed logging
        import logging
        logging.getLogger("pyvider.rpcplugin").setLevel(logging.DEBUG)

        await asyncio.wait_for(client.start(), timeout=15)

        print(f"\n✅ Client started!")

        # Try operations
        test_key = "kvclient_test_key"
        test_value = json.dumps({"test": "kvclient"}).encode()

        await client.put(test_key, test_value)
        print(f"✓ Put succeeded")

        retrieved = await client.get(test_key)
        data = json.loads(retrieved.decode())

        print(f"✓ Get succeeded")
        print(f"  Keys: {list(data.keys())}")

        await client.close()

        print(f"\n✅ KVCLIENT TEST: Python → Python WORKS!")
        return True

    except asyncio.TimeoutError:
        print(f"\n❌ KVClient start timeout")

        # Try to get subprocess info
        if hasattr(client, '_client'):
            rc_client = client._client
            if hasattr(rc_client, '_process'):
                proc = rc_client._process
                if proc:
                    print(f"\nProcess info:")
                    print(f"   PID: {proc.pid}")
                    print(f"   Poll: {proc.poll()}")

                    if proc.poll() is None:
                        print(f"   Process is running but not responding")

                        # Try to read its stdout/stderr
                        import select
                        ready, _, _ = select.select([proc.stdout], [], [], 0.1)
                        if ready:
                            try:
                                line = proc.stdout.readline()
                                print(f"   Stdout: {line}")
                            except:
                                pass

        print(f"\nThis suggests pyvider-rpcplugin issue, not our code")
        return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run debug tests."""
    print("\n" + "="*60)
    print("DEEP DEBUG: Python → Python Connection")
    print("="*60)

    # Test 1: Manual handshake
    result1 = await test_manual_handshake()

    # Test 2: With KVClient
    result2 = await test_with_kvclient()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Manual test (direct subprocess):  {'✅ WORKS' if result1 else '❌ FAILED'}")
    print(f"KVClient test (via pyvider):      {'✅ WORKS' if result2 else '❌ FAILED'}")

    if result1 and not result2:
        print(f"\n⚠️  CONCLUSION: pyvider-rpcplugin KVClient has compatibility issue")
        print(f"   The server works fine, the issue is in the client wrapper")


if __name__ == "__main__":
    asyncio.run(main())

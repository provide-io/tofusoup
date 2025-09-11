#
# tofusoup/harness/python/tests_rpc/souptest_rpc_pyclient_goserver.py
#
# tofusoup/harness/python/tests_rpc/souptest_rpc_pyclient_goserver.py
#
# tofusoup/harness/python/tests_rpc/souptest_rpc_pyclient_goserver.py
#

import os  # For os.access and crypto options via env for client
from pathlib import Path

import pytest

from tofusoup.rpc.client import KVClient

# This test relies on the `go_kvstore_harness` fixture defined in
# `tofusoup/src/tofusoup/harness/python/conftest.py` (or eventually `conformance/conftest.py`)
# That fixture is responsible for ensuring the Go KVStore server harness is built
# and returning the path to its executable.


@pytest.mark.asyncio
async def test_pyclient_goserver_put_get(go_kvstore_harness: Path, tmp_path: Path) -> None:
    """
    Tests Put and Get operations between Python KVClient and the Go KVServer harness.
    The go_kvstore_harness fixture provides the path to the compiled Go server executable.
    The KVClient will start this Go server as a subprocess.
    """
    if not go_kvstore_harness.exists() or not os.access(go_kvstore_harness, os.X_OK):
        pytest.skip(
            f"Go KVStore harness executable not found or not executable at {go_kvstore_harness}"
        )

    # For the Go server, crypto options are passed as command-line arguments to the harness.
    # The KVClient starts the server executable directly.
    # To test different crypto parameters for the Go server, the `go_kvstore_harness` fixture
    # itself would need to be parameterized to launch the Go server with different CLI args,
    # or the test would need to orchestrate this launch with specific args.

    # For this test, we'll use the default cert generation of the Go server harness.
    # Client-side crypto options are passed to KVClient constructor.
    # These will set env vars like PLUGIN_CLIENT_CERT_ALGO.
    # Their effectiveness depends on pyvider-rpcplugin client part.

    # Example: Test with specific client-side crypto settings (effectiveness depends on pyvider-rpcplugin)
    # For now, let's test without specific client crypto to ensure baseline works.
    client = KVClient(server_path=str(go_kvstore_harness))

    # To test with client crypto options:
    # client = KVClient(
    #     server_path=str(go_kvstore_harness),
    #     cert_algo="ecdsa", # Example
    #     cert_curve="P256"  # Example
    # )

    try:
        await client.start()  # This starts the Go server subprocess

        key = "test_py_go_key"
        value_str = "Hello from PyClient to GoServer!"
        value_bytes = value_str.encode("utf-8")

        await client.put(key, value_bytes)

        retrieved_value = await client.get(key)

        assert retrieved_value is not None
        assert retrieved_value.decode("utf-8") == value_str

        # Test getting a non-existent key
        retrieved_non_existent = await client.get("non_existent_key_py_go")
        assert retrieved_non_existent is None

    except Exception as e:
        # Attempt to include server's stderr if available (KVClient's _relay_stderr logs it)
        # For more direct access, KVClient might need to store last few stderr lines.
        pytest.fail(
            f"PyClient-GoServer test failed: {e}. Check logs for Go server stderr via KVClient's relay."
        )
    finally:
        if client:
            await client.close()  # This stops the Go server subprocess


# <3 🍲 🍜 🍥>


# 🍲🥄🧪🪄

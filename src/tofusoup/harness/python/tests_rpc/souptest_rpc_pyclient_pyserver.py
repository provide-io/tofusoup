#
# tofusoup/harness/python/tests_rpc/souptest_rpc_pyclient_pyserver.py
#
# tofusoup/harness/python/tests_rpc/souptest_rpc_pyclient_pyserver.py
#
# tofusoup/harness/python/tests_rpc/souptest_rpc_pyclient_pyserver.py
#

from pathlib import Path

import pytest

# Unused: import subprocess, time, tempfile, os
from tofusoup.rpc.client import KVClient

# For starting the server, we'd typically call the tofusoup CLI command
# or directly use the server's start function if it's easily importable and manageable.


# Placeholder for server process management.
# A proper fixture in conftest.py would be better.
@pytest.fixture(scope="module")
async def python_kv_server_process():
    """Starts the Python KV server as a subprocess for testing."""
    # Assuming tofusoup is installed and in path, or use sys.executable
    # We need to ensure the server runs in the background and we can get its port/endpoint.
    # The current tofusoup.rpc.server.start_kv_server() is a blocking call.
    # For testing, it might need to be adapted or run via `soup rpc kv server-start --py`
    # and its process managed.

    # This is a simplified placeholder. Real implementation needs robust process management
    # and a way to know when the server is ready (e.g., specific log output or health check).
    # The current `start_kv_server` blocks, so it's not directly usable in a fixture background.
    # We'll assume for now that `soup rpc kv server-start --py` can be run.
    # The `pyvider-rpcplugin` uses environment variables for communication, not a fixed port for TCP.
    # It typically uses named pipes or UDS on Unix.

    # For this placeholder, we'll just note that a server needs to be running.
    # In a real scenario, we'd start `soup rpc kv server-start --py`
    # and manage its lifecycle.
    # For now, this fixture doesn't actually start a server, tests will need a live one
    # or this needs to be implemented properly.

    # Let's try to run it as a subprocess.
    # This requires finding the tofusoup executable or using python -m tofusoup.cli
    tofusoup_exe = "tofusoup"  # Or find path via shutil.which or sys.executable + "-m tofusoup.cli"
    server_cmd = [tofusoup_exe, "rpc", "kv", "server-start", "--py"]

    # Using a temporary directory for KV store data, if server uses relative paths or specific tmp locations.
    # The current server uses /tmp/kv-data-*

    # Need to capture server output to know when it's ready, or wait a fixed time.
    # Also need to manage PLUGIN_HOST_ADDRESS for the client if the server outputs it.
    # pyvider-rpcplugin server usually prints "plugin address" to stdout.

    process = None
    plugin_address = None
    try:
        # Start the server process
        # Redirect stdout to capture the plugin address
        # Set a unique PLUGIN_SERVER_PATH for this server instance for the client to pick up.
        # This is complex because the client also tries to start the server if not using a fixed path.
        # For PyClient vs PyServer, they would typically run in the same process for test simplicity
        # or the test would orchestrate two separate processes.

        # Let's assume for this test, the server is started MANUALLY or by a higher-level test runner.
        # This test will try to connect to a server whose details are passed via env.
        # This fixture will be a NO-OP for now, highlighting the need for external server setup
        # or a more sophisticated fixture.
        # logger.warning("Python KV server fixture is a placeholder and does not start a server automatically.")
        # For now, these tests will likely fail unless a server is running.
        # A better approach for testing PyClient vs PyServer would be in-process if possible,
        # or a test harness that launches the server via `soup rpc kv server-start --py`
        # and then launches the client actions.

        # For the purpose of this file creation, let's assume a very basic subprocess management
        # that might not be robust enough for actual CI.
        # The server writes to /tmp, so no special data dir needed for this basic test.
        # The client connects using a path to the server executable, which is not what we're testing here.
        # This test is PyClient vs PyServer.

        # The `tofusoup.rpc.server.start_kv_server()` is an async function that blocks.
        # We need to run it in a separate process for the client to connect.
        # This is more of an integration test.

        # This fixture needs to be more advanced, likely using `multiprocessing` or `asyncio.create_subprocess_exec`
        # and managing the server lifecycle.
        # For now, we'll skip automatic server startup in this fixture.
        # The tests will assume the server is started by some other means if these are run directly.
        # Or, these tests would be integration tests run by `soup test rpc`.

        # This placeholder is insufficient. Actual RPC tests will require proper server lifecycle management.
        # For now, I will write a test that *would* run if a server was available.
        yield None
    finally:
        # if process and process.poll() is None:
        #     process.terminate()
        #     process.wait(timeout=5)
        pass


# This client also needs a server path. For Py-Py tests, this is tricky.
# If the server is run as a plugin by pyvider-rpcplugin, it's via a path to a script.
# For now, let's assume the client will connect to a server started by `soup rpc kv server-start --py`
# and the address is somehow known (e.g. fixed if not using go-plugin style dynamic addressing).
# The current `KVClient` requires a `server_path` to an executable, which is not how Py-Py usually works
# unless the Python server is also launched as a "plugin" executable by the client.

# The `tofusoup.rpc.cli.kv_server_start_command` when using `--py` directly calls `python_start_kv_server()`.
# This server uses `pyvider.rpcplugin.server.RPCPluginServer`.
# The `pyvider.rpcplugin.client.RPCPluginClient` expects a command to run for the server.

# This suggests that for PyClient vs PyServer tests using this framework,
# the Python server itself should be packaged or invoked as an executable script.
# Let `tofusoup/src/tofusoup/rpc/server.py` be that script.
# The client will then be configured with the path to this script.


@pytest.mark.asyncio
async def test_pyclient_pyserver_put_get(tmp_path):
    """
    Tests Put and Get operations between Python KVClient and Python KVServer.
    This test assumes `tofusoup/src/tofusoup/rpc/server.py` can act as a server executable.
    It further assumes that the `RPCPluginServer` started by `server.py`
    and `RPCPluginClient` used by `KVClient` can communicate (e.g. mTLS auto-negotiation).
    """
    python_server_script_path = (
        Path(__file__).resolve().parents[4] / "src/tofusoup/rpc/server.py"
    )
    if not python_server_script_path.exists():
        pytest.skip(f"Python KV server script not found at {python_server_script_path}")

    # The KVClient will attempt to start the server_path as a subprocess.
    # We need to ensure that the environment is set up correctly for this subprocess,
    # especially PYTHONPATH if tofusoup and pyvider are not installed globally in that env.
    # The `env.sh` script sets up the venv. When subprocess Popen is called, it might inherit env.

    # Create a unique temp directory for this test's server data to avoid collisions
    # The server currently writes to /tmp/kv-data-{key}. This needs to be made configurable
    # or tests need to manage this. For now, we accept this global state.

    # The client internally starts the server process.
    # The `plugin_env_for_server` in KVClient includes PLUGIN_AUTO_MTLS="true"
    # The `RPCPluginServer` in `server.py` also defaults to mTLS. They should work together.

    client = KVClient(server_path=str(python_server_script_path))

    try:
        await client.start()

        key = "test_py_py_key"
        value_str = "Hello from PyClient to PyServer!"
        value_bytes = value_str.encode("utf-8")

        await client.put(key, value_bytes)

        retrieved_value = await client.get(key)

        assert retrieved_value is not None
        assert retrieved_value.decode("utf-8") == value_str

        # Test getting a non-existent key
        retrieved_non_existent = await client.get("non_existent_key_py_py")
        assert retrieved_non_existent is None

    except Exception as e:
        # Log stderr from client._client._process if available
        stderr_output = "N/A"
        if (
            client
            and client._client
            and client._client._process
            and hasattr(client._client._process, "stderr_output_for_test")
        ):
            stderr_output = client._client._process.stderr_output_for_test  # type: ignore
        pytest.fail(
            f"PyClient-PyServer test failed: {e}\nServer stderr:\n{stderr_output}"
        )
    finally:
        if client:
            await client.close()


# Note: This test structure relies heavily on RPCPluginClient being able to launch
# the rpc/server.py script and establish communication. This is essentially an integration
# test of the Python client and server using the pyvider-rpcplugin mechanisms.
# Simpler unit tests for KVHandler logic (if isolated from gRPC) would also be valuable.

# <3 🍲 🍜 🍥>


# 🍲🥄🧪🪄

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Core logic for RPC operations, including test orchestration."""

import asyncio
import pathlib

from provide.foundation import logger

# from typing import Tuple, Any, Coroutine # Not used
from rich import print as rich_print

from tofusoup.harness.logic import ensure_go_harness_build
from tofusoup.rpc.client import KVClient

# Configuration
GO_KV_HARNESS_NAME = "go-rpc"  # Updated from "kvstore-go" to align with harness.logic
# GO_KV_SERVER_BINARY_NAME = "kvstore-server-go" # Seems unused
# PYTHON_SERVER_PORT = 50051 # Unused with dynamic addressing
# GO_SERVER_PORT = 50052 # Unused with dynamic addressing

TEST_KEY = "compat_test_key"
TEST_VALUE_PY = b"value_from_python_client_for_python_server"
TEST_VALUE_GO = b"value_from_python_client_for_go_server"


async def _run_client_operations(client: KVClient, key: str, value_to_put: bytes, server_type: str) -> bool:
    """Helper to run Put and Get operations and verify."""
    try:
        await client.put(key, value_to_put)
        logger.info(f"Client PUT '{key}' to {server_type} server successful.")
        retrieved_value = await client.get(key)
        if retrieved_value == value_to_put:
            logger.info(f"Client GET '{key}' from {server_type} server successful and value matches.")
            return True
        else:
            logger.error(
                f"Client GET from {server_type} server: Value mismatch. Expected '{value_to_put}', got '{retrieved_value}'"
            )
            return False
    except Exception as e:
        logger.error(f"Client operations against {server_type} server failed: {e}", exc_info=True)
        return False


async def _test_with_python_server(project_root: pathlib.Path, loaded_config: dict) -> bool:
    logger.info("Starting Python KV server for testing...")
    python_server_script_path = project_root / "src" / "tofusoup" / "rpc" / "server.py"
    if not python_server_script_path.exists():
        logger.error(f"Python KV server script not found at {python_server_script_path}.")
        return False

    client = None
    success = False
    try:
        # KVClient will start server.py as a subprocess.
        client = KVClient(
            server_path=str(python_server_script_path),
            tls_mode="auto",
            tls_key_type="ec",
        )

        await client.start()
        logger.info("Python client connected to Python KV server (via subprocess).")
        success = await _run_client_operations(client, TEST_KEY, TEST_VALUE_PY, "Python (subprocess)")
    except Exception as e:
        logger.error(f"Python Client vs Python Server test failed: {e}", exc_info=True)
        success = False
    finally:
        if client:
            await client.close()
    return success


async def _test_with_go_server(
    project_root: pathlib.Path, go_server_executable: pathlib.Path, loaded_config: dict
) -> bool:
    logger.info(f"Testing with Go KV server from: {go_server_executable}")
    client = None
    success = False
    try:
        # KVClient handles starting the Go server subprocess.
        client = KVClient(
            server_path=str(go_server_executable),
            tls_mode="auto",
            tls_key_type="ec",
        )
        await client.start()
        logger.info("Python client connected to Go KV server.")
        success = await _run_client_operations(client, TEST_KEY, TEST_VALUE_GO, "Go")

    except FileNotFoundError:
        logger.error(f"Go KV server executable not found at {go_server_executable}.")
        return False
    except Exception as e:
        logger.error(f"Error during Go KV server test: {e}", exc_info=True)
        return False
    finally:
        if client:
            await client.close()
    return success


def run_rpc_compatibility_tests(project_root: pathlib.Path, loaded_config: dict) -> bool:
    """
    Runs RPC compatibility tests:
    - Python Client vs Go Server
    - Python Client vs Python Server
    """
    logger.info("Running RPC compatibility tests...")
    overall_success = True

    # --- Test Python Client vs Go Server ---
    rich_print("\n[bold cyan]--- Testing: Python Client vs. Go KV Server ---[/bold cyan]")
    try:
        go_server_executable = ensure_go_harness_build(GO_KV_HARNESS_NAME, project_root, loaded_config)
        if not go_server_executable or not go_server_executable.exists():
            logger.error(
                f"Go KV server executable (from harness '{GO_KV_HARNESS_NAME}') not found or build failed."
            )
            py_client_vs_go_server_success = False
        else:
            logger.info(f"Found Go KV server executable: {go_server_executable}")
            py_client_vs_go_server_success = asyncio.run(
                _test_with_go_server(project_root, go_server_executable, loaded_config)
            )
    except Exception as e:
        logger.error(f"Failed to build or locate Go KV server harness: {e}", exc_info=True)
        py_client_vs_go_server_success = False

    if py_client_vs_go_server_success:
        rich_print("[bold green]Python Client vs. Go Server: PASSED[/bold green]")
    else:
        rich_print("[bold red]Python Client vs. Go Server: FAILED[/bold red]")
        overall_success = False

    # --- Test Python Client vs Python Server ---
    rich_print("\n[bold cyan]--- Testing: Python Client vs. Python KV Server ---[/bold cyan]")
    try:
        py_client_vs_py_server_success = asyncio.run(_test_with_python_server(project_root, loaded_config))
    except Exception as e:
        logger.error(f"Python Client vs Python Server test execution failed: {e}", exc_info=True)
        py_client_vs_py_server_success = False

    if py_client_vs_py_server_success:
        rich_print("[bold green]Python Client vs. Python Server: PASSED[/bold green]")
    else:
        rich_print("[bold red]Python Client vs. Python Server: FAILED[/bold red]")
        overall_success = False

    if overall_success:
        logger.info("All RPC compatibility tests passed.")
    else:
        logger.error("One or more RPC compatibility tests failed.")

    return overall_success


# 🥣🔬🔚

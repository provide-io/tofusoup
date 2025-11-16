#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive RPC K/V Matrix Testing

Tests all 20 combinations of client/server/crypto configurations:
- 2 client languages (Python KVClient, Go soup-go subprocess)
- 2 server languages (Go via `soup-go`, Python via server module)
- 5 crypto configs (RSA 2048/4096, EC 256/384/521)

Pattern matches souptest_rpc_kv_matrix.py:
- Python client tests use KVClient library with asyncio
- Go client tests use subprocess to call soup-go executable
- Both test actual functionality: PUT raw data, GET same data

Verifies:
1. K/V storage isolation per combination
2. Data integrity (PUT stores what GET retrieves)
3. Cross-language RPC compatibility
"""

import os
from pathlib import Path
import shutil
import subprocess
import uuid

from provide.foundation import logger
import pytest

from tofusoup.common.config import load_tofusoup_config
from tofusoup.harness.logic import ensure_go_harness_build
from tofusoup.rpc.client import KVClient

from .matrix_config import RPC_KV_CRYPTO_CONFIGS, CryptoConfig


class TestRPCMatrixComprehensivePythonClient:
    """RPC K/V matrix testing using Python KVClient with Python server only.

    Note: Python client → Go server is NOT currently supported by pyvider-rpcplugin.
    This tests Python client with Python servers across all crypto configs.

    (Go client tests cover Go-to-Go and Go-to-Python combinations)
    """

    @pytest.mark.integration_rpc
    @pytest.mark.harness_python
    @pytest.mark.parametrize("crypto_config", RPC_KV_CRYPTO_CONFIGS)
    async def test_python_client_to_python_server(
        self, crypto_config: CryptoConfig, tmp_path: Path, project_root: Path
    ) -> None:
        """
        Test RPC K/V operations using Python KVClient with Python server.

        This test verifies that KVClient can:
        1. Start a Python server subprocess
        2. Complete go-plugin handshake with auto-mTLS
        3. PUT a key-value pair
        4. GET the same key and retrieve the correct value

        Matrix coverage: 1 client (Python) x 1 server (Python) x 5 crypto configs = 5 test combinations

        Note: Python client → Go server is not supported by pyvider-rpcplugin and is tested
        via Go client instead (TestRPCMatrixComprehensiveGoClient).
        """

        logger.info(f"Testing KVClient → Python server with {crypto_config.name}")

        # Use soup CLI binary for Python server
        soup_path = shutil.which("soup")
        if not soup_path:
            pytest.skip("soup executable not found in PATH")
        server_path = soup_path

        # Create isolated test directory
        test_dir = tmp_path / f"kvclient_python_{crypto_config.name}"
        test_dir.mkdir()

        # Set storage directory via environment variable
        storage_dir = test_dir / "kv-storage"
        storage_dir.mkdir(parents=True, exist_ok=True)
        os.environ["KV_STORAGE_DIR"] = str(storage_dir)

        # Generate unique test data
        test_key = f"py-matrix-test-{uuid.uuid4()}"
        test_value = f"value-python-{crypto_config.name}".encode()

        # Create KVClient with specified crypto config
        client = KVClient(
            server_path=server_path,
            tls_mode=crypto_config.auth_mode,
            tls_key_type=crypto_config.key_type if crypto_config.key_type == "rsa" else "ec",
            tls_curve=(f"secp{crypto_config.key_size}r1" if crypto_config.key_type == "ec" else None),
        )

        try:
            # Start client (which starts server subprocess and handles handshake)
            await client.start()
            logger.info("KVClient connected to Python server")

            # Test 1: PUT operation
            await client.put(test_key, test_value)
            logger.debug(f"PUT {test_key} completed")

            # Test 2: GET operation - verify correct value
            retrieved_value = await client.get(test_key)
            assert retrieved_value == test_value, (
                f"Value mismatch: expected {test_value!r}, got {retrieved_value!r}"
            )
            logger.debug(f"GET {test_key} verified")

            logger.info(f"✅ KVClient → Python server ({crypto_config.name}) verified")

        finally:
            await client.close()


class TestRPCMatrixComprehensiveGoClient:
    """RPC K/V matrix testing using Go client (soup-go) with server spawning.

    Tests Go client with both Go and Python servers across all crypto configs.
    """

    @pytest.mark.integration_rpc
    @pytest.mark.harness_go
    @pytest.mark.harness_python
    @pytest.mark.parametrize("server_lang", ["go", "python"])
    @pytest.mark.parametrize("crypto_config", RPC_KV_CRYPTO_CONFIGS)
    async def test_go_client_basic_operations(
        self, server_lang: str, crypto_config: CryptoConfig, tmp_path: Path, project_root: Path
    ) -> None:
        """
        Test RPC K/V operations using Go client (soup-go) with specified server language.

        This test verifies that soup-go client can:
        1. Launch a server subprocess (Go or Python) via PLUGIN_SERVER_PATH
        2. Complete go-plugin handshake with auto-mTLS
        3. PUT a key-value pair
        4. GET the same key and retrieve the correct value
        5. Handle non-existent keys appropriately

        Matrix coverage: 2 server langs x 5 crypto configs = 10 test combinations
        """

        logger.info(f"Testing soup-go client → {server_lang} server with {crypto_config.name}")

        # Get soup-go client path
        config = load_tofusoup_config(project_root)
        soup_go_path = str(ensure_go_harness_build("soup-go", project_root, config))

        # Get server path based on language
        if server_lang == "go":
            server_path = soup_go_path  # soup-go acts as both client and server
        else:  # python
            soup_path = shutil.which("soup")
            if not soup_path:
                pytest.skip("soup executable not found in PATH")
            server_path = soup_path

        # Create isolated test directory
        test_dir = tmp_path / f"go_client_{server_lang}_{crypto_config.name}"
        test_dir.mkdir()

        # Set storage directory via environment variable
        storage_dir = test_dir / "kv-storage"
        storage_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique test data
        test_key = f"go-matrix-test-{uuid.uuid4()}"
        test_value = f"value-{server_lang}-{crypto_config.name}"

        # Prepare environment for soup-go client
        env = os.environ.copy()
        env["PLUGIN_SERVER_PATH"] = server_path
        env["KV_STORAGE_DIR"] = str(storage_dir)

        # Set TLS configuration for server via environment
        if crypto_config.key_type == "ec":
            env["TLS_MODE"] = crypto_config.auth_mode
            env["TLS_KEY_TYPE"] = "ec"
            env["TLS_CURVE"] = f"secp{crypto_config.key_size}r1"
        else:  # rsa
            env["TLS_MODE"] = crypto_config.auth_mode
            env["TLS_KEY_TYPE"] = "rsa"
            env["TLS_KEY_SIZE"] = str(crypto_config.key_size)

        try:
            # Test 1: PUT operation
            logger.debug(f"PUT {test_key} = {test_value}")
            put_result = subprocess.run(
                [soup_go_path, "rpc", "kv", "put", test_key, test_value],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert put_result.returncode == 0, (
                f"PUT failed with exit code {put_result.returncode}\n"
                f"stdout: {put_result.stdout}\n"
                f"stderr: {put_result.stderr}"
            )
            logger.debug("PUT completed successfully")

            # Test 2: GET operation - verify correct value
            logger.debug(f"GET {test_key}")
            get_result = subprocess.run(
                [soup_go_path, "rpc", "kv", "get", test_key],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert get_result.returncode == 0, (
                f"GET failed with exit code {get_result.returncode}\n"
                f"stdout: {get_result.stdout}\n"
                f"stderr: {get_result.stderr}"
            )

            retrieved_value = get_result.stdout.strip()
            assert retrieved_value == test_value, (
                f"Value mismatch: expected {test_value!r}, got {retrieved_value!r}"
            )
            logger.debug(f"GET {test_key} = {retrieved_value} (verified)")

            # Test 3: GET non-existent key - should exit with non-zero
            non_existent_key = f"does-not-exist-{uuid.uuid4()}"
            logger.debug(f"GET {non_existent_key} (expecting not found)")
            get_missing_result = subprocess.run(
                [soup_go_path, "rpc", "kv", "get", non_existent_key],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # soup-go should exit with error code for missing key
            assert get_missing_result.returncode != 0, (
                f"Expected non-zero exit code for missing key, got {get_missing_result.returncode}"
            )
            logger.debug(f"GET {non_existent_key} = not found (expected)")

            logger.info(f"✅ Go client → {server_lang} server ({crypto_config.name}) verified")

        except subprocess.TimeoutExpired as e:
            pytest.fail(f"Command timed out after 30s: {e.cmd}\nstdout: {e.stdout}\nstderr: {e.stderr}")


# 🥣🔬🔚

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive RPC K/V Matrix Testing

Tests all 20 combinations of client/server/crypto configurations:
- 2 client languages (Go, Python via `soup` CLI)
- 2 server languages (Go via `soup-go`, Python via server module)
- 5 crypto configs (RSA 2048/4096, EC 256/384/521)

Uses subprocess pattern to test actual CLI commands:
- Python client: `soup rpc kv {put|get}`
- Go client: `soup-go rpc kv {put|get}`

Verifies:
1. K/V storage isolation per combination
2. Data integrity (PUT stores what GET retrieves)
3. Cross-language RPC compatibility
"""

import os
from pathlib import Path
import subprocess
import uuid

from provide.foundation import logger
import pytest

from tofusoup.common.config import load_tofusoup_config
from tofusoup.harness.logic import ensure_go_harness_build
import tofusoup.rpc.server as py_server_module

from .matrix_config import RPC_KV_CRYPTO_CONFIGS, CryptoConfig


class TestRPCMatrixComprehensivePythonClient:
    """RPC K/V matrix testing using Python client (soup CLI) with server spawning.

    Tests Python client with both Go and Python servers across all crypto configs.
    """

    @pytest.mark.integration_rpc
    @pytest.mark.harness_go
    @pytest.mark.harness_python
    @pytest.mark.parametrize("server_lang", ["go", "python"])
    @pytest.mark.parametrize("crypto_config", RPC_KV_CRYPTO_CONFIGS)
    async def test_python_client_basic_operations(
        self, server_lang: str, crypto_config: CryptoConfig, tmp_path: Path, project_root: Path
    ) -> None:
        """
        Test RPC K/V operations using Python client (soup) with specified server language.

        This test verifies that soup client can:
        1. Launch a server subprocess (Go or Python) via PLUGIN_SERVER_PATH
        2. Complete go-plugin handshake with auto-mTLS
        3. PUT a key-value pair
        4. GET the same key and retrieve the correct value
        5. Handle non-existent keys appropriately

        Matrix coverage: 2 server langs x 5 crypto configs = 10 test combinations
        """

        logger.info(f"Testing soup client → {server_lang} server with {crypto_config.name}")

        # Get server path based on language
        if server_lang == "go":
            config = load_tofusoup_config(project_root)
            server_path = str(ensure_go_harness_build("soup-go", project_root, config))
        else:  # python
            server_path = str(Path(py_server_module.__file__))

        # Create isolated test directory
        test_dir = tmp_path / f"soup_client_{server_lang}_{crypto_config.name}"
        test_dir.mkdir()

        # Set storage directory via environment variable
        storage_dir = test_dir / "kv-storage"
        storage_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique test data
        test_key = f"py-matrix-test-{uuid.uuid4()}"
        test_value = f"value-{server_lang}-{crypto_config.name}"

        # Prepare environment for soup client
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
                ["soup", "rpc", "kv", "put", test_key, test_value],
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
            logger.debug(f"PUT completed successfully")

            # Test 2: GET operation - verify correct value
            logger.debug(f"GET {test_key}")
            get_result = subprocess.run(
                ["soup", "rpc", "kv", "get", test_key],
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
                ["soup", "rpc", "kv", "get", non_existent_key],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # soup should exit with error code for missing key
            assert get_missing_result.returncode != 0, (
                f"Expected non-zero exit code for missing key, got {get_missing_result.returncode}"
            )
            logger.debug(f"GET {non_existent_key} = not found (expected)")

            logger.info(f"✅ Python client → {server_lang} server ({crypto_config.name}) verified")

        except subprocess.TimeoutExpired as e:
            pytest.fail(f"Command timed out after 30s: {e.cmd}\nstdout: {e.stdout}\nstderr: {e.stderr}")


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
            server_path = str(Path(py_server_module.__file__))

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
            logger.debug(f"PUT completed successfully")

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

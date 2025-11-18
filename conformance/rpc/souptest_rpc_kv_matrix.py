#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""RPC K/V Matrix Testing

Tests combinations of:
- Server languages: go (soup-go), python (tofusoup.rpc.server)
- Crypto configurations: auto_mtls with RSA 2048/4096, EC 256/384/521

Uses KVClient (wraps pyvider-rpcplugin) which properly handles:
- Server lifecycle management
- go-plugin handshake protocol
- Auto-mTLS certificate generation
- gRPC channel management

This is the CORRECT way to test RPC - using the proper abstractions
instead of manually managing processes and handshakes.
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


class TestRPCKVMatrix:
    """RPC K/V matrix testing using proper KVClient abstractions."""

    @pytest.mark.integration_rpc
    @pytest.mark.harness_go
    @pytest.mark.harness_python
    @pytest.mark.parametrize("server_lang", ["go", "python"])
    @pytest.mark.parametrize("crypto_config", RPC_KV_CRYPTO_CONFIGS)
    async def test_rpc_kv_basic_operations(
        self, server_lang: str, crypto_config: CryptoConfig, tmp_path: Path, project_root: Path
    ) -> None:
        """
        Test basic RPC K/V operations using KVClient (pyvider-rpcplugin).

        This test verifies that KVClient can successfully:
        1. Start a server subprocess (Go or Python)
        2. Complete go-plugin handshake with auto-mTLS
        3. PUT a key-value pair
        4. GET the same key and retrieve the correct value
        5. Handle non-existent keys appropriately

        Matrix coverage: 2 server langs x 5 crypto configs = 10 test combinations
        """

        logger.info(f"Testing KVClient → {server_lang} server with {crypto_config.name}")

        # Get server path based on language
        if server_lang == "go":
            config = load_tofusoup_config(project_root)
            server_path = str(ensure_go_harness_build("soup-go", project_root, config))
        else:  # python
            soup_path = shutil.which("soup")
            if not soup_path:
                pytest.skip("soup executable not found in PATH")
            server_path = soup_path

        # Create isolated test directory
        test_dir = tmp_path / f"kvclient_{server_lang}_{crypto_config.name}"
        test_dir.mkdir()

        # Generate unique test data
        test_key = f"matrix-test-{uuid.uuid4()}"
        test_value = f"value-{server_lang}-{crypto_config.name}".encode()

        # Set storage directory via environment variable
        storage_dir = test_dir / "kv-storage"
        storage_dir.mkdir(parents=True, exist_ok=True)
        os.environ["KV_STORAGE_DIR"] = str(storage_dir)

        # Create KVClient - it handles server lifecycle and handshake
        client = KVClient(
            server_path=server_path,
            tls_mode=crypto_config.auth_mode,
            tls_key_type=crypto_config.key_type if crypto_config.key_type == "rsa" else "ec",
            tls_curve=(f"secp{crypto_config.key_size}r1" if crypto_config.key_type == "ec" else None),
        )

        try:
            # Start client (which starts server subprocess and handles handshake)
            await client.start()
            logger.info(f"KVClient connected to {server_lang} server")

            # Test 1: PUT operation
            await client.put(test_key, test_value)
            logger.debug(f"PUT {test_key} = {test_value.decode()}")

            # Test 2: GET operation - verify correct value
            retrieved_value = await client.get(test_key)
            assert retrieved_value is not None, f"GET returned None for key '{test_key}'"
            assert retrieved_value == test_value, (
                f"Value mismatch: expected {test_value!r}, got {retrieved_value!r}"
            )
            logger.debug(f"GET {test_key} = {retrieved_value.decode()}")

            # Test 3: GET non-existent key
            non_existent_key = f"does-not-exist-{uuid.uuid4()}"
            non_existent_value = await client.get(non_existent_key)
            assert non_existent_value is None, (
                f"Expected None for non-existent key, got {non_existent_value!r}"
            )
            logger.debug(f"GET {non_existent_key} = None (expected)")

        finally:
            # Clean up
            await client.close()

    @pytest.mark.integration_rpc
    @pytest.mark.harness_go
    @pytest.mark.harness_python
    @pytest.mark.parametrize("server_lang", ["go", "python"])
    @pytest.mark.parametrize("crypto_config", RPC_KV_CRYPTO_CONFIGS)
    async def test_rpc_kv_multiple_keys(
        self, server_lang: str, crypto_config: CryptoConfig, tmp_path: Path, project_root: Path
    ) -> None:
        """
        Test multiple key operations using KVClient.

        This test verifies that:
        1. Multiple keys can be stored independently
        2. Retrieving one key doesn't affect others
        3. Keys with similar names are handled correctly
        """

        logger.info(f"Testing multiple keys: KVClient → {server_lang} ({crypto_config.name})")

        # Get server path
        if server_lang == "go":
            config = load_tofusoup_config(project_root)
            server_path = str(ensure_go_harness_build("soup-go", project_root, config))
        else:
            soup_path = shutil.which("soup")
            if not soup_path:
                pytest.skip("soup executable not found in PATH")
            server_path = soup_path

        # Create test directory
        test_dir = tmp_path / f"kvclient_{server_lang}_{crypto_config.name}_multi"
        test_dir.mkdir()

        # Set storage directory via environment variable
        storage_dir = test_dir / "kv-storage"
        storage_dir.mkdir(parents=True, exist_ok=True)
        os.environ["KV_STORAGE_DIR"] = str(storage_dir)

        # Create KVClient
        client = KVClient(
            server_path=server_path,
            tls_mode=crypto_config.auth_mode,
            tls_key_type=crypto_config.key_type if crypto_config.key_type == "rsa" else "ec",
            tls_curve=(f"secp{crypto_config.key_size}r1" if crypto_config.key_type == "ec" else None),
        )

        try:
            await client.start()

            # Store multiple keys
            keys = {f"key-{i}": f"value-{i}".encode() for i in range(5)}

            # PUT all keys
            for key, value in keys.items():
                await client.put(key, value)

            # GET all keys and verify
            for key, expected_value in keys.items():
                retrieved_value = await client.get(key)
                assert retrieved_value == expected_value

        finally:
            await client.close()


class TestRPCKVMatrixGoClient:
    """RPC K/V matrix testing using Go client (soup-go) with server spawning.

    This test class uses soup-go's built-in server spawning capability via
    the PLUGIN_SERVER_PATH environment variable. soup-go handles:
    - Server subprocess launch
    - go-plugin handshake protocol
    - Auto-mTLS certificate generation
    - TLS configuration from handshake
    - Server cleanup after operation

    This is the standard go-plugin client pattern - the client owns and manages
    the server lifecycle.
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
        Test basic RPC K/V operations using Go client (soup-go).

        This test verifies that soup-go client can:
        1. Launch a server subprocess (Go or Python) via PLUGIN_SERVER_PATH
        2. Complete go-plugin handshake with auto-mTLS
        3. PUT a key-value pair
        4. GET the same key and retrieve the correct value
        5. Handle non-existent keys appropriately

        Matrix coverage: 2 server langs x 5 crypto configs = 10 test combinations

        Known issue: Go client → Python server has implementation bug causing TLS handshake failure.
        Works: Go → Go ✅
        Fails: Go → Python ⚠️ (implementation bug, not fundamental limitation)
        """

        # # Mark Python server tests as expected failure (implementation bug)
        # if server_lang == "python":
        #     pytest.xfail(
        #         "Go client → Python server failing with TLS handshake error. "
        #         "Error: 'tls: first record does not look like a TLS handshake'. "
        #         "This is an implementation bug in soup-go or test configuration, NOT a fundamental "
        #         "Go↔Python TLS limitation (Terraform successfully uses Go→pyvider with TLS). "
        #         "Needs investigation - likely TLS mode detection or handshake parsing issue."
        #     )

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
        # PLUGIN_SERVER_PATH tells soup-go which binary to launch as server
        env = os.environ.copy()
        env["PLUGIN_SERVER_PATH"] = server_path
        env["KV_STORAGE_DIR"] = str(storage_dir)

        # Set TLS configuration for server via environment
        # (soup-go server reads these when launched)
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
            # soup-go will spawn server, handle handshake, execute PUT, cleanup
            logger.debug(f"PUT {test_key} = {test_value}")
            put_result = subprocess.run(
                [soup_go_path, "rpc", "kv", "put", test_key, test_value],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,  # Allow time for server spawn + handshake + operation
            )

            assert put_result.returncode == 0, (
                f"PUT failed with exit code {put_result.returncode}\n"
                f"stdout: {put_result.stdout}\n"
                f"stderr: {put_result.stderr}"
            )
            logger.debug("PUT completed successfully")

            # Test 2: GET operation - verify correct value
            # soup-go will spawn server again, handle handshake, execute GET, cleanup
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

        except subprocess.TimeoutExpired as e:
            pytest.fail(f"Command timed out after 30s: {e.cmd}\nstdout: {e.stdout}\nstderr: {e.stderr}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")

    @pytest.mark.integration_rpc
    @pytest.mark.harness_go
    @pytest.mark.harness_python
    @pytest.mark.parametrize("server_lang", ["go", "python"])
    @pytest.mark.parametrize("crypto_config", RPC_KV_CRYPTO_CONFIGS)
    async def test_go_client_multiple_keys(
        self, server_lang: str, crypto_config: CryptoConfig, tmp_path: Path, project_root: Path
    ) -> None:
        """
        Test multiple key operations using Go client (soup-go).

        This test verifies that:
        1. Multiple keys can be stored independently
        2. Retrieving one key doesn't affect others
        3. Keys with similar names are handled correctly
        4. soup-go can spawn server multiple times in sequence

        Known issue: Go client → Python server has implementation bug causing TLS handshake failure.
        Works: Go → Go ✅
        Fails: Go → Python ⚠️ (implementation bug, not fundamental limitation)
        """

        # # Mark Python server tests as expected failure (implementation bug)
        # if server_lang == "python":
        #     pytest.xfail(
        #         "Go client → Python server failing with TLS handshake error. "
        #         "Error: 'tls: first record does not look like a TLS handshake'. "
        #         "This is an implementation bug in soup-go or test configuration, NOT a fundamental "
        #         "Go↔Python TLS limitation (Terraform successfully uses Go→pyvider with TLS). "
        #         "Needs investigation - likely TLS mode detection or handshake parsing issue."
        #     )

        logger.info(f"Testing multiple keys: soup-go → {server_lang} ({crypto_config.name})")

        # Get soup-go client path
        config = load_tofusoup_config(project_root)
        soup_go_path = str(ensure_go_harness_build("soup-go", project_root, config))

        # Get server path
        if server_lang == "go":
            server_path = soup_go_path
        else:
            soup_path = shutil.which("soup")
            if not soup_path:
                pytest.skip("soup executable not found in PATH")
            server_path = soup_path

        # Create test directory
        test_dir = tmp_path / f"go_client_{server_lang}_{crypto_config.name}_multi"
        test_dir.mkdir()

        # Set storage directory
        storage_dir = test_dir / "kv-storage"
        storage_dir.mkdir(parents=True, exist_ok=True)

        # Prepare environment
        env = os.environ.copy()
        env["PLUGIN_SERVER_PATH"] = server_path
        env["KV_STORAGE_DIR"] = str(storage_dir)

        # Set TLS configuration
        if crypto_config.key_type == "ec":
            env["TLS_MODE"] = crypto_config.auth_mode
            env["TLS_KEY_TYPE"] = "ec"
            env["TLS_CURVE"] = f"secp{crypto_config.key_size}r1"
        else:
            env["TLS_MODE"] = crypto_config.auth_mode
            env["TLS_KEY_TYPE"] = "rsa"
            env["TLS_KEY_SIZE"] = str(crypto_config.key_size)

        try:
            # Store multiple keys
            keys = {f"key-{i}": f"value-{i}" for i in range(5)}

            # PUT all keys (each spawns server, operates, cleans up)
            for key, value in keys.items():
                logger.debug(f"PUT {key} = {value}")
                put_result = subprocess.run(
                    [soup_go_path, "rpc", "kv", "put", key, value],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                assert put_result.returncode == 0, f"PUT {key} failed: {put_result.stderr}"

            # GET all keys and verify (each spawns server again)
            for key, expected_value in keys.items():
                logger.debug(f"GET {key}")
                get_result = subprocess.run(
                    [soup_go_path, "rpc", "kv", "get", key],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                assert get_result.returncode == 0, f"GET {key} failed: {get_result.stderr}"

                retrieved_value = get_result.stdout.strip()
                assert retrieved_value == expected_value, (
                    f"Value mismatch for {key}: expected {expected_value!r}, got {retrieved_value!r}"
                )

            logger.debug(f"All {len(keys)} keys verified successfully")

        except subprocess.TimeoutExpired as e:
            pytest.fail(f"Command timed out after 30s: {e.cmd}\nstdout: {e.stdout}\nstderr: {e.stderr}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")


# 🥣🔬🔚

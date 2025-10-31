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

from pathlib import Path
import uuid

from provide.foundation import logger
import pytest

from tofusoup.rpc.client import KVClient
from tofusoup.common.config import load_tofusoup_config
from tofusoup.harness.logic import ensure_go_harness_build
from .matrix_config import RPC_KV_CRYPTO_CONFIGS, CryptoConfig
import tofusoup.rpc.server as py_server_module


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

        Matrix coverage: 2 server langs × 5 crypto configs = 10 test combinations
        """

        logger.info(f"Testing KVClient → {server_lang} server with {crypto_config.name}")

        # Get server path based on language
        if server_lang == "go":
            config = load_tofusoup_config(project_root)
            server_path = str(ensure_go_harness_build("soup-go", project_root, config))
        else:  # python
            server_path = str(Path(py_server_module.__file__))

        # Create isolated test directory
        test_dir = tmp_path / f"kvclient_{server_lang}_{crypto_config.name}"
        test_dir.mkdir()

        # Generate unique test data
        test_key = f"matrix-test-{uuid.uuid4()}"
        test_value = f"value-{server_lang}-{crypto_config.name}".encode()

        # Create KVClient - it handles server lifecycle and handshake
        client = KVClient(
            server_path=server_path,
            tls_mode=crypto_config.auth_mode,
            tls_key_type=crypto_config.key_type if crypto_config.key_type == "rsa" else "ec",
            tls_curve=(
                f"secp{crypto_config.key_size}r1" if crypto_config.key_type == "ec" else None
            ),
            storage_dir=test_dir / "kv-storage",
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
            server_path = str(Path(py_server_module.__file__))

        # Create test directory
        test_dir = tmp_path / f"kvclient_{server_lang}_{crypto_config.name}_multi"
        test_dir.mkdir()

        # Create KVClient
        client = KVClient(
            server_path=server_path,
            tls_mode=crypto_config.auth_mode,
            tls_key_type=crypto_config.key_type if crypto_config.key_type == "rsa" else "ec",
            tls_curve=(
                f"secp{crypto_config.key_size}r1" if crypto_config.key_type == "ec" else None
            ),
            storage_dir=test_dir / "kv-storage",
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


# 🥣🔬🔚

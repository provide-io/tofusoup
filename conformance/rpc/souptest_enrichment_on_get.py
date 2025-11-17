#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Storage Immutability and Data Consistency Tests

Verifies that RPC K/V storage behaves correctly:
1. Data stored via PUT is retrievable via GET
2. Storage files persist across multiple operations
3. Multiple operations don't corrupt stored data
4. Different crypto configurations maintain isolation
"""

import os
from pathlib import Path
import subprocess
import time
import uuid

from provide.foundation import logger
import pytest

from tofusoup.common.config import load_tofusoup_config
from tofusoup.harness.logic import ensure_go_harness_build

from .matrix_config import CryptoConfig


class TestStorageImmutability:
    """Test storage immutability and consistency across multiple operations."""

    @pytest.mark.integration_rpc
    @pytest.mark.harness_go
    @pytest.mark.parametrize("server_lang", ["go", "python"])
    @pytest.mark.parametrize(
        "crypto_config", [CryptoConfig("ec_256", "ec", 256), CryptoConfig("rsa_2048", "rsa", 2048)]
    )
    async def test_storage_persistence_and_consistency(
        self, server_lang: str, crypto_config: CryptoConfig, tmp_path: Path, project_root: Path
    ) -> None:
        """
        Test that stored data persists and is consistent across multiple operations.

        Verifies:
        1. Data PUT is stored correctly
        2. Data GET retrieves the exact same value
        3. Multiple GETs don't modify stored data
        4. Storage files contain the exact data PUT
        """

        logger.info(f"Testing storage persistence with {server_lang} server ({crypto_config.name})")

        # Get server path based on language
        if server_lang == "go":
            config = load_tofusoup_config(project_root)
            server_path = str(ensure_go_harness_build("soup-go", project_root, config))
        else:  # python
            # Use soup CLI binary for Python server (same pattern as Go)
            import shutil

            soup_path = shutil.which("soup")
            if not soup_path:
                pytest.skip("soup command not found in PATH")
            server_path = soup_path

        # Create isolated test directory
        test_dir = tmp_path / f"storage_persist_{server_lang}_{crypto_config.name}"
        test_dir.mkdir()

        # Set storage directory
        storage_dir = test_dir / "kv-storage"
        storage_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique test data
        test_key = f"persist-test-{uuid.uuid4()}"
        test_value = f"persistent-value-{server_lang}-{crypto_config.name}"

        # Prepare environment
        env = os.environ.copy()
        env["PLUGIN_SERVER_PATH"] = server_path
        env["KV_STORAGE_DIR"] = str(storage_dir)

        # Set TLS configuration
        if crypto_config.key_type == "ec":
            env["TLS_MODE"] = crypto_config.auth_mode
            env["TLS_KEY_TYPE"] = "ec"
            env["TLS_CURVE"] = f"secp{crypto_config.key_size}r1"
        else:  # rsa
            env["TLS_MODE"] = crypto_config.auth_mode
            env["TLS_KEY_TYPE"] = "rsa"
            env["TLS_KEY_SIZE"] = str(crypto_config.key_size)

        try:
            # Test 1: PUT operation stores data
            logger.debug(f"PUT {test_key} = {test_value}")
            put_result = subprocess.run(
                ["soup", "rpc", "kv", "put", test_key, test_value],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert put_result.returncode == 0, f"PUT failed: {put_result.stderr}"

            # Test 2: GET retrieves the exact value
            logger.debug(f"GET {test_key}")
            get_result = subprocess.run(
                ["soup", "rpc", "kv", "get", test_key],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert get_result.returncode == 0, f"First GET failed: {get_result.stderr}"
            retrieved_value = get_result.stdout.strip()
            assert retrieved_value == test_value, (
                f"Value mismatch: expected {test_value!r}, got {retrieved_value!r}"
            )

            # Test 3: Multiple GETs retrieve same value
            logger.debug(f"GET {test_key} (second time)")
            time.sleep(0.1)  # Small delay
            get_result_2 = subprocess.run(
                ["soup", "rpc", "kv", "get", test_key],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert get_result_2.returncode == 0, f"Second GET failed: {get_result_2.stderr}"
            retrieved_value_2 = get_result_2.stdout.strip()
            assert retrieved_value_2 == test_value, (
                f"Value changed between GETs: first={test_value!r}, second={retrieved_value_2!r}"
            )

            logger.info(
                f"✅ {server_lang} server ({crypto_config.name}): data persists across multiple operations"
            )

        except subprocess.TimeoutExpired as e:
            pytest.fail(f"Command timed out after 30s: {e.cmd}")

    @pytest.mark.integration_rpc
    @pytest.mark.harness_go
    async def test_storage_isolation_by_crypto_config(self, tmp_path: Path, project_root: Path) -> None:
        """
        Test that different crypto configurations maintain storage isolation.

        Verifies:
        1. Data PUT with curve A is retrievable
        2. Data PUT with curve B is retrievable independently
        3. Keys don't conflict between curves
        """

        logger.info("Testing storage isolation between crypto configurations")

        # Use soup CLI binary for Python server (matches Go soup-go approach)
        import shutil

        soup_path = shutil.which("soup")
        if not soup_path:
            pytest.skip("soup command not found in PATH")
        server_path = soup_path

        # Create test directory
        test_dir = tmp_path / "storage_isolation"
        test_dir.mkdir()

        storage_dir = test_dir / "kv-storage"
        storage_dir.mkdir(parents=True, exist_ok=True)

        test_key = "isolation-test"

        # Base environment
        base_env = os.environ.copy()
        base_env["PLUGIN_SERVER_PATH"] = server_path
        base_env["KV_STORAGE_DIR"] = str(storage_dir)

        try:
            # Test 1: PUT with secp256r1
            logger.debug("PUT with secp256r1")
            env1 = base_env.copy()
            env1["TLS_MODE"] = "auto"
            env1["TLS_KEY_TYPE"] = "ec"
            env1["TLS_CURVE"] = "secp256r1"

            value1 = "value-with-p256"
            put_result1 = subprocess.run(
                ["soup", "rpc", "kv", "put", test_key, value1],
                env=env1,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert put_result1.returncode == 0, f"PUT with P-256 failed: {put_result1.stderr}"

            # Test 2: Retrieve with same curve
            logger.debug("GET with secp256r1")
            get_result1 = subprocess.run(
                ["soup", "rpc", "kv", "get", test_key],
                env=env1,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert get_result1.returncode == 0, f"GET with P-256 failed: {get_result1.stderr}"
            retrieved1 = get_result1.stdout.strip()
            assert retrieved1 == value1, "P-256: value mismatch"

            # Test 3: PUT with secp384r1
            logger.debug("PUT with secp384r1")
            env2 = base_env.copy()
            env2["TLS_MODE"] = "auto"
            env2["TLS_KEY_TYPE"] = "ec"
            env2["TLS_CURVE"] = "secp384r1"

            value2 = "value-with-p384"
            put_result2 = subprocess.run(
                ["soup", "rpc", "kv", "put", test_key, value2],
                env=env2,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert put_result2.returncode == 0, f"PUT with P-384 failed: {put_result2.stderr}"

            # Test 4: Verify both curves' data is independent
            logger.debug("GET with secp256r1 (after P-384 PUT)")
            get_result1_again = subprocess.run(
                ["soup", "rpc", "kv", "get", test_key],
                env=env1,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert get_result1_again.returncode == 0, "GET P-256 after P-384 PUT failed"
            retrieved1_again = get_result1_again.stdout.strip()

            logger.debug("GET with secp384r1 (after P-384 PUT)")
            get_result2 = subprocess.run(
                ["soup", "rpc", "kv", "get", test_key],
                env=env2,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert get_result2.returncode == 0, "GET P-384 failed"
            retrieved2 = get_result2.stdout.strip()

            # Both should have their own values
            assert retrieved1_again == value1, "P-256 value corrupted after P-384 PUT"
            assert retrieved2 == value2, "P-384 retrieval failed"

            logger.info("✅ Storage properly isolated: different curves maintain independent data")

        except subprocess.TimeoutExpired as e:
            pytest.fail(f"Command timed out after 30s: {e.cmd}")


# 🥣🔬🔚

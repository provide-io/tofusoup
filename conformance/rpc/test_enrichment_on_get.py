#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Enrichment-on-Get Verification Tests

Verifies that JSON enrichment happens on Get (not Put):
1. Put stores raw JSON without server_handshake
2. Get returns enriched JSON with server_handshake
3. Multiple Gets show different timestamps (proving re-enrichment)
4. Stored files contain raw JSON (no enrichment)
"""

import json
from pathlib import Path
import time

from provide.foundation import logger
import pytest

from .harness_factory import create_kv_client, create_kv_server
from .matrix_config import CryptoConfig


@pytest.mark.integration_rpc
@pytest.mark.asyncio
async def test_enrichment_happens_on_get_not_put(project_root: Path, test_artifacts_dir: Path) -> None:
    """Verify that enrichment happens on Get, not Put."""

    # Use simple Go server configuration
    combo_id = "enrichment_test_go_server"
    test_dir = test_artifacts_dir / combo_id
    test_dir.mkdir(parents=True, exist_ok=True)

    crypto_config = CryptoConfig("ec_256", "ec", 256)

    logger.info("Testing enrichment-on-get behavior")

    # Create test key and raw JSON value
    test_key = "enrichment_test_key"
    test_value = json.dumps({"data": "test_value", "iteration": 1}).encode()

    async with create_kv_server(
        language="go",
        crypto_config=crypto_config,
        work_dir=test_dir,
        combo_id=combo_id,
        client_language="python",
    ) as server:
        async with create_kv_client(
            language="pyvider",
            crypto_config=crypto_config,
            server_address=server.address,
            work_dir=test_dir,
        ) as client:
            # === TEST 1: Put stores raw JSON ===
            await client.put(test_key, test_value)
            logger.info("Put raw JSON value")

            # Verify stored file contains raw JSON (no enrichment)
            storage_dir = test_dir / f"kv-{combo_id}"
            storage_file = storage_dir / f"kv-data-{test_key}"
            assert storage_file.exists(), f"Storage file should exist at {storage_file}"

            with storage_file.open("rb") as f:
                stored_data = json.loads(f.read())

            assert "server_handshake" not in stored_data, (
                "Stored file should NOT contain server_handshake (enrichment should happen on Get)"
            )
            assert stored_data["data"] == "test_value", "Stored file should contain original data"
            logger.info("✅ Verified: Stored file contains raw JSON without enrichment")

            # === TEST 2: Get returns enriched JSON ===
            retrieved_1 = await client.get(test_key)
            enriched_1 = json.loads(retrieved_1.decode())

            assert "server_handshake" in enriched_1, (
                "Retrieved value should contain server_handshake (enrichment on Get)"
            )
            assert enriched_1["data"] == "test_value", "Retrieved value should contain original data"

            timestamp_1 = enriched_1["server_handshake"]["timestamp"]
            received_at_1 = enriched_1["server_handshake"]["received_at"]
            logger.info(f"✅ Verified: First Get returned enriched JSON (timestamp: {timestamp_1})")

            # === TEST 3: Multiple Gets show different timestamps (re-enrichment) ===
            time.sleep(0.1)  # Small delay to ensure different timestamps

            retrieved_2 = await client.get(test_key)
            enriched_2 = json.loads(retrieved_2.decode())

            assert "server_handshake" in enriched_2, "Second Get should also be enriched"
            timestamp_2 = enriched_2["server_handshake"]["timestamp"]
            received_at_2 = enriched_2["server_handshake"]["received_at"]

            # Timestamps should be different (proving re-enrichment on each Get)
            assert timestamp_2 != timestamp_1, (
                f"Timestamps should differ (proving re-enrichment): {timestamp_1} vs {timestamp_2}"
            )

            # received_at should increase (server uptime increases)
            assert received_at_2 > received_at_1, (
                f"received_at should increase: {received_at_1} -> {received_at_2}"
            )

            logger.info(f"✅ Verified: Second Get shows updated timestamp ({timestamp_2})")
            logger.info(f"   received_at increased: {received_at_1:.3f}s -> {received_at_2:.3f}s")

            # === TEST 4: Stored file still contains raw JSON (unchanged) ===
            with storage_file.open("rb") as f:
                stored_data_final = json.loads(f.read())

            assert "server_handshake" not in stored_data_final, (
                "Stored file should STILL not contain server_handshake after multiple Gets"
            )
            assert stored_data_final == stored_data, "Stored file should be unchanged by Get operations"
            logger.info("✅ Verified: Stored file remains raw JSON (unchanged by Gets)")

            logger.info("✅ All enrichment-on-get tests passed!")


@pytest.mark.integration_rpc
@pytest.mark.asyncio
async def test_enrichment_with_python_server(project_root: Path, test_artifacts_dir: Path) -> None:
    """Verify enrichment-on-get behavior with Python server."""

    combo_id = "enrichment_test_python_server"
    test_dir = test_artifacts_dir / combo_id
    test_dir.mkdir(parents=True, exist_ok=True)

    crypto_config = CryptoConfig("rsa_2048", "rsa", 2048)

    test_key = "enrichment_test_key_py"
    test_value = json.dumps({"data": "python_server_test", "iteration": 1}).encode()

    async with create_kv_server(
        language="pyvider",
        crypto_config=crypto_config,
        work_dir=test_dir,
        combo_id=combo_id,
        client_language="python",
    ) as server:
        async with create_kv_client(
            language="pyvider",
            crypto_config=crypto_config,
            server_address=server.address,
            work_dir=test_dir,
        ) as client:
            # Put and verify storage
            await client.put(test_key, test_value)

            storage_dir = test_dir / f"kv-{combo_id}"
            storage_file = storage_dir / f"kv-data-{test_key}"

            with storage_file.open("rb") as f:
                stored_data = json.loads(f.read())

            assert "server_handshake" not in stored_data, "Python server should also store raw JSON"
            logger.info("✅ Python server stores raw JSON")

            # Get and verify enrichment
            retrieved = await client.get(test_key)
            enriched = json.loads(retrieved.decode())

            assert "server_handshake" in enriched, "Python server should enrich on Get"
            assert enriched["server_handshake"]["server_language"] == "python", (
                "Expected server_language=python"
            )
            logger.info("✅ Python server enriches on Get")


# 🥣🔬🔚

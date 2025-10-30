#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive RPC K/V Matrix Testing

Tests all 20 combinations of client/server/crypto configurations:
- 2 client languages (Go, Python)
- 2 server languages (Go, Python)
- 5 crypto configs (RSA 2048/4096, EC 256/384/521)

Verifies:
1. K/V storage isolation per combination
2. JSON enrichment with combo metadata on Get
3. Correct combo identification in server_handshake
"""

import json
from pathlib import Path

from provide.foundation import logger
import pytest

from .harness_factory import create_kv_client, create_kv_server
from .matrix_config import RPC_KV_MATRIX_PARAMS


@pytest.mark.integration_rpc
@pytest.mark.parametrize("client_lang,server_lang,crypto_config", RPC_KV_MATRIX_PARAMS)
@pytest.mark.asyncio
async def test_rpc_matrix_comprehensive(
    client_lang: str,
    server_lang: str,
    crypto_config: "CryptoConfig",
    project_root: Path,
    test_artifacts_dir: Path,
) -> None:
    """Test all RPC client/server/crypto combinations with isolation and enrichment verification."""

    # Create combo-specific directory for isolation
    combo_id = f"{client_lang}_client_{server_lang}_server_{crypto_config.name}"
    test_dir = test_artifacts_dir / combo_id
    test_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Testing combination: {combo_id}")

    # Create test key and value
    test_key = f"test_{combo_id}"
    test_value = json.dumps(
        {
            "test_name": combo_id,
            "client_language": client_lang,
            "server_language": server_lang,
            "crypto_config": crypto_config.name,
            "key_type": crypto_config.key_type,
            "key_size": crypto_config.key_size,
        }
    ).encode()

    # Start server with combo identification
    async with create_kv_server(
        language=server_lang,
        crypto_config=crypto_config,
        work_dir=test_dir,
        combo_id=combo_id,
        client_language=client_lang,
    ) as server:
        logger.info(f"Server started at {server.address}")

        # Start client and perform Put/Get operations
        async with create_kv_client(
            language=client_lang,
            crypto_config=crypto_config,
            server_address=server.address,
            work_dir=test_dir,
        ) as client:
            # Put raw JSON
            await client.put(test_key, test_value)
            logger.info(f"Put value for key: {test_key}")

            # Get enriched JSON
            retrieved = await client.get(test_key)
            assert retrieved is not None, f"Failed to retrieve key: {test_key}"

            # Parse enriched JSON
            enriched_data = json.loads(retrieved.decode())
            logger.info(f"Retrieved enriched value: {json.dumps(enriched_data, indent=2)}")

            # === VERIFICATION ASSERTIONS ===

            # 1. Original data should be present
            assert enriched_data["test_name"] == combo_id
            assert enriched_data["client_language"] == client_lang
            assert enriched_data["server_language"] == server_lang

            # 2. Server handshake should be added
            assert "server_handshake" in enriched_data, "Server should enrich JSON with server_handshake"
            server_handshake = enriched_data["server_handshake"]

            # 3. Verify combo identification in server_handshake
            assert server_handshake["server_language"] == server_lang, (
                f"Expected server_language={server_lang}, got {server_handshake.get('server_language')}"
            )
            assert server_handshake["client_language"] == client_lang, (
                f"Expected client_language={client_lang}, got {server_handshake.get('client_language')}"
            )
            assert server_handshake["combo_id"] == combo_id, (
                f"Expected combo_id={combo_id}, got {server_handshake.get('combo_id')}"
            )

            # 4. Verify crypto_config in server_handshake
            assert "crypto_config" in server_handshake, "Server should include crypto_config"
            crypto_info = server_handshake["crypto_config"]
            assert crypto_info["key_type"] == crypto_config.key_type, (
                f"Expected key_type={crypto_config.key_type}, got {crypto_info.get('key_type')}"
            )

            if crypto_config.key_type == "rsa":
                assert crypto_info["key_size"] == crypto_config.key_size, (
                    f"Expected key_size={crypto_config.key_size}, got {crypto_info.get('key_size')}"
                )
            elif crypto_config.key_type == "ec":
                # EC should have curve name
                curve_map = {256: "secp256r1", 384: "secp384r1", 521: "secp521r1"}
                expected_curve = curve_map.get(crypto_config.key_size)
                if expected_curve:
                    assert crypto_info.get("curve") == expected_curve, (
                        f"Expected curve={expected_curve}, got {crypto_info.get('curve')}"
                    )

            # 5. Verify storage isolation - check file exists in combo-specific directory
            storage_dir = test_dir / f"kv-{combo_id}"
            storage_file = storage_dir / f"kv-data-{test_key}"
            assert storage_file.exists(), (
                f"Storage file should exist at {storage_file}"
            )

            # Read the stored file and verify it's RAW (not enriched)
            with storage_file.open("rb") as f:
                stored_data = json.loads(f.read())

            # The stored file should NOT have server_handshake (enrichment is on Get)
            assert "server_handshake" not in stored_data, (
                "Stored file should contain raw JSON without enrichment (enrichment happens on Get)"
            )

            logger.info(f"✅ Combination {combo_id} verified successfully")
            logger.info(f"   Storage: {storage_file}")
            logger.info(f"   Server: {server_handshake['server_language']}")
            logger.info(f"   Client: {server_handshake['client_language']}")
            logger.info(f"   Crypto: {crypto_config.name}")


# 🥣🔬🔚

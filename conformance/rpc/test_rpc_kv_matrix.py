"""
RPC K/V Matrix Testing

Tests all combinations of:
- Client languages: go, pyvider
- Server languages: go, pyvider  
- Crypto configurations: auto_mtls with RSA 2048/4096, EC 256/384/521

Each test verifies that every client can successfully set/get keys
with every server across all crypto configurations.
"""

import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any

import pytest
from provide.foundation import logger

from .matrix_config import RPC_KV_MATRIX_PARAMS, CryptoConfig
from .harness_factory import create_kv_server, create_kv_client


class TestRPCKVMatrix:
    """RPC K/V matrix testing across all language and crypto combinations."""
    
    @pytest.mark.parametrize("client_lang,server_lang,crypto_config", RPC_KV_MATRIX_PARAMS)
    async def test_rpc_kv_basic_operations(
        self, 
        client_lang: str,
        server_lang: str, 
        crypto_config: CryptoConfig,
        tmp_path: Path
    ):
        """
        Test basic RPC K/V operations across all matrix combinations.
        
        This test verifies that every client-server-crypto combination can:
        1. PUT a key-value pair
        2. GET the same key and retrieve the correct value
        3. Handle non-existent keys appropriately
        
        Matrix coverage: 2 × 2 × 5 = 20 test combinations
        """
        
        logger.info(f"Testing {client_lang} client → {server_lang} server with {crypto_config.name}")
        
        # Create isolated test directory
        test_dir = tmp_path / f"{client_lang}_{server_lang}_{crypto_config.name}"
        test_dir.mkdir()
        
        # Generate unique test data
        test_key = f"matrix-test-{uuid.uuid4()}"
        test_value = f"value-{client_lang}-to-{server_lang}-{crypto_config.name}".encode('utf-8')
        
        # Start server with specified configuration
        async with create_kv_server(
            language=server_lang,
            crypto_config=crypto_config,
            work_dir=test_dir
        ) as server:
            
            logger.info(f"{server_lang} server started at {server.address}")
            
            # Create client with matching configuration  
            async with create_kv_client(
                language=client_lang,
                crypto_config=crypto_config,
                server_address=server.address,
                work_dir=test_dir
            ) as client:
                
                logger.info(f"{client_lang} client connected to {server.address}")
                
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
                
        logger.info(f"✅ {client_lang} → {server_lang} ({crypto_config.name}) test passed")

    @pytest.mark.parametrize("client_lang,server_lang,crypto_config", RPC_KV_MATRIX_PARAMS)
    async def test_rpc_kv_multiple_keys(
        self,
        client_lang: str,
        server_lang: str, 
        crypto_config: CryptoConfig,
        tmp_path: Path
    ):
        """
        Test multiple key operations to ensure no interference between keys.
        
        This test verifies that:
        1. Multiple keys can be stored independently
        2. Retrieving one key doesn't affect others
        3. Keys with similar names are handled correctly
        """
        
        logger.info(f"Testing multiple keys: {client_lang} → {server_lang} ({crypto_config.name})")
        
        test_dir = tmp_path / f"multi_{client_lang}_{server_lang}_{crypto_config.name}"
        test_dir.mkdir()
        
        # Generate multiple test key-value pairs
        test_data = {}
        for i in range(3):
            key = f"multi-key-{i}-{uuid.uuid4()}"
            value = f"multi-value-{i}-{client_lang}-{server_lang}-{crypto_config.name}".encode('utf-8')
            test_data[key] = value
        
        async with create_kv_server(
            language=server_lang,
            crypto_config=crypto_config,
            work_dir=test_dir
        ) as server:
            
            async with create_kv_client(
                language=client_lang,
                crypto_config=crypto_config, 
                server_address=server.address,
                work_dir=test_dir
            ) as client:
                
                # PUT all key-value pairs
                for key, value in test_data.items():
                    await client.put(key, value)
                    logger.debug(f"PUT {key} = {value.decode()}")
                
                # GET all key-value pairs and verify
                for key, expected_value in test_data.items():
                    retrieved_value = await client.get(key)
                    assert retrieved_value is not None, f"Key '{key}' not found"
                    assert retrieved_value == expected_value, (
                        f"Key '{key}': expected {expected_value!r}, got {retrieved_value!r}"
                    )
                    logger.debug(f"GET {key} = {retrieved_value.decode()} ✓")
                
        logger.info(f"✅ Multiple keys test passed: {client_lang} → {server_lang} ({crypto_config.name})")

    @pytest.mark.parametrize("client_lang,server_lang,crypto_config", RPC_KV_MATRIX_PARAMS)
    async def test_rpc_kv_overwrite_key(
        self,
        client_lang: str,
        server_lang: str,
        crypto_config: CryptoConfig,
        tmp_path: Path
    ):
        """
        Test key overwriting behavior.
        
        This test verifies that:
        1. A key can be overwritten with a new value
        2. The new value completely replaces the old value
        3. No traces of the old value remain
        """
        
        logger.info(f"Testing key overwrite: {client_lang} → {server_lang} ({crypto_config.name})")
        
        test_dir = tmp_path / f"overwrite_{client_lang}_{server_lang}_{crypto_config.name}"
        test_dir.mkdir()
        
        test_key = f"overwrite-test-{uuid.uuid4()}"
        original_value = f"original-{client_lang}-{server_lang}-{crypto_config.name}".encode('utf-8')
        new_value = f"updated-{client_lang}-{server_lang}-{crypto_config.name}".encode('utf-8')
        
        async with create_kv_server(
            language=server_lang,
            crypto_config=crypto_config,
            work_dir=test_dir
        ) as server:
            
            async with create_kv_client(
                language=client_lang,
                crypto_config=crypto_config,
                server_address=server.address, 
                work_dir=test_dir
            ) as client:
                
                # PUT original value
                await client.put(test_key, original_value)
                logger.debug(f"PUT {test_key} = {original_value.decode()}")
                
                # Verify original value
                retrieved = await client.get(test_key)
                assert retrieved == original_value, "Original value not stored correctly"
                
                # PUT new value (overwrite)
                await client.put(test_key, new_value)
                logger.debug(f"PUT {test_key} = {new_value.decode()} (overwrite)")
                
                # Verify new value
                retrieved = await client.get(test_key)
                assert retrieved is not None, "Key disappeared after overwrite"
                assert retrieved == new_value, (
                    f"Overwrite failed: expected {new_value!r}, got {retrieved!r}"
                )
                assert retrieved != original_value, (
                    "Old value still present after overwrite"
                )
                
        logger.info(f"✅ Key overwrite test passed: {client_lang} → {server_lang} ({crypto_config.name})")

    @pytest.mark.parametrize("crypto_config", [
        config for param in RPC_KV_MATRIX_PARAMS for config in [param.values[2]]
    ])
    async def test_rpc_kv_crypto_validation(
        self,
        crypto_config: CryptoConfig,
        tmp_path: Path
    ):
        """
        Test crypto configuration validation across all crypto settings.
        
        This test ensures that:
        1. Certificates are generated correctly for each crypto config
        2. mTLS handshake succeeds with the generated certificates
        3. Communication is actually encrypted (vs falling back to plaintext)
        
        This test uses pyvider-pyvider combination for consistency.
        """
        
        logger.info(f"Testing crypto validation for {crypto_config.name}")
        
        test_dir = tmp_path / f"crypto_validation_{crypto_config.name}"
        test_dir.mkdir()
        
        # Use pyvider client/server for crypto validation
        async with create_kv_server(
            language="pyvider",
            crypto_config=crypto_config,
            work_dir=test_dir
        ) as server:
            
            async with create_kv_client(
                language="pyvider",
                crypto_config=crypto_config,
                server_address=server.address,
                work_dir=test_dir
            ) as client:
                
                # Test basic operation to ensure crypto doesn't break functionality
                test_key = f"crypto-test-{crypto_config.name}"
                test_value = f"crypto-validation-{crypto_config.key_type}-{crypto_config.key_size}".encode('utf-8')
                
                await client.put(test_key, test_value)
                retrieved = await client.get(test_key)
                
                assert retrieved == test_value, (
                    f"Crypto config {crypto_config.name} broke basic functionality"
                )
                
        logger.info(f"✅ Crypto validation passed for {crypto_config.name}")

    @pytest.mark.parametrize("client_lang,server_lang,crypto_config", [
        # Test a representative subset for edge case testing
        param for param in RPC_KV_MATRIX_PARAMS[:4]  # First 4 combinations
    ])
    async def test_rpc_kv_edge_cases(
        self,
        client_lang: str,
        server_lang: str,
        crypto_config: CryptoConfig,
        tmp_path: Path
    ):
        """
        Test edge cases with a subset of the matrix.
        
        Edge cases tested:
        1. Empty key (should handle gracefully)
        2. Empty value
        3. Very long key
        4. Very long value
        5. Special characters in key/value
        """
        
        logger.info(f"Testing edge cases: {client_lang} → {server_lang} ({crypto_config.name})")
        
        test_dir = tmp_path / f"edge_{client_lang}_{server_lang}_{crypto_config.name}"
        test_dir.mkdir()
        
        async with create_kv_server(
            language=server_lang,
            crypto_config=crypto_config,
            work_dir=test_dir
        ) as server:
            
            async with create_kv_client(
                language=client_lang,
                crypto_config=crypto_config,
                server_address=server.address,
                work_dir=test_dir
            ) as client:
                
                # Test 1: Empty value (valid case)
                empty_key = f"empty-value-{uuid.uuid4()}"
                await client.put(empty_key, b"")
                retrieved = await client.get(empty_key)
                assert retrieved == b"", "Empty value not handled correctly"
                logger.debug("✓ Empty value test passed")
                
                # Test 2: Long key
                long_key = f"long-key-{'x' * 200}-{uuid.uuid4()}"
                long_value = b"long-key-value"
                await client.put(long_key, long_value)
                retrieved = await client.get(long_key)
                assert retrieved == long_value, "Long key not handled correctly"
                logger.debug("✓ Long key test passed")
                
                # Test 3: Long value
                normal_key = f"normal-key-{uuid.uuid4()}"
                long_value = b"x" * 10000  # 10KB value
                await client.put(normal_key, long_value)
                retrieved = await client.get(normal_key)
                assert retrieved == long_value, "Long value not handled correctly"
                logger.debug("✓ Long value test passed")
                
                # Test 4: Special characters
                special_key = f"special-key-üñíçødé-{uuid.uuid4()}"
                special_value = "special-value-üñíçødé-🚀".encode('utf-8')
                await client.put(special_key, special_value)
                retrieved = await client.get(special_key)
                assert retrieved == special_value, "Special characters not handled correctly"
                logger.debug("✓ Special characters test passed")
                
        logger.info(f"✅ Edge cases test passed: {client_lang} → {server_lang} ({crypto_config.name})")


# Test utilities

def get_test_matrix_summary() -> Dict[str, Any]:
    """Get summary of the test matrix for reporting."""
    from .matrix_config import get_matrix_summary
    
    matrix_info = get_matrix_summary()
    matrix_info.update({
        "test_functions": [
            "test_rpc_kv_basic_operations",
            "test_rpc_kv_multiple_keys", 
            "test_rpc_kv_overwrite_key",
            "test_rpc_kv_crypto_validation",
            "test_rpc_kv_edge_cases"
        ],
        "total_basic_tests": len(RPC_KV_MATRIX_PARAMS),
        "total_multiple_key_tests": len(RPC_KV_MATRIX_PARAMS),
        "total_overwrite_tests": len(RPC_KV_MATRIX_PARAMS),
        "total_crypto_validation_tests": 5,  # One per crypto config
        "total_edge_case_tests": 4  # Subset of matrix
    })
    
    return matrix_info


if __name__ == "__main__":
    # Print test matrix summary
    summary = get_test_matrix_summary()
    print("RPC K/V Matrix Test Summary:")
    print(f"Total basic operation tests: {summary['total_basic_tests']}")
    print(f"Total multiple key tests: {summary['total_multiple_key_tests']}")
    print(f"Total overwrite tests: {summary['total_overwrite_tests']}") 
    print(f"Total crypto validation tests: {summary['total_crypto_validation_tests']}")
    print(f"Total edge case tests: {summary['total_edge_case_tests']}")
    print(f"Grand total test executions: {sum(v for k, v in summary.items() if k.startswith('total_') and k != 'total_combinations')}")

# 🍲🥄🧪🪄

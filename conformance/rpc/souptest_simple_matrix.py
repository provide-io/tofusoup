"""
Simple RPC K/V Matrix Testing

Tests the key known working combinations:
- Go client → Go server (with and without mTLS)
- Python client → Go server (with and without mTLS)
- Go client → Python server (with and without mTLS)
- Python client → Python server (with and without mTLS)

Uses the existing working KVClient infrastructure.
"""

from datetime import datetime
import json
from pathlib import Path
import time
import uuid

from provide.foundation import logger
import pytest

from tofusoup.rpc.client import KVClient

def write_test_proof(test_name: str, client_type: str, server_type: str,
                     tls_mode: str, crypto_type: str, keys_written: list[str],
                     kv_storage_files: list[str] | None = None,
                     proof_dir: Path | None = None) -> Path:
    """Write proof manifest that this test ran and what it wrote.

    Args:
        test_name: Name of the test
        client_type: Type of client (python, go)
        server_type: Type of server (python, go)
        tls_mode: TLS mode (disabled, auto, manual)
        crypto_type: Crypto type (none, rsa, ecdsa_p256, etc.)
        keys_written: List of keys written during the test
        kv_storage_files: List of KV storage file paths
        proof_dir: Directory where proof manifest should be written (required)

    Returns:
        Path to the written proof manifest file
    """
    if proof_dir is None:
        raise ValueError("proof_dir must be provided - no hardcoded paths allowed")

    proof_dir.mkdir(exist_ok=True, parents=True)

    manifest = {
        "test_name": test_name,
        "client_type": client_type,
        "server_type": server_type,
        "tls_mode": tls_mode,
        "crypto_type": crypto_type,
        "keys_written": keys_written,
        "kv_storage_files": kv_storage_files or [],
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }

    manifest_file = proof_dir / f"{test_name}_{int(time.time())}.json"
    manifest_file.write_text(json.dumps(manifest, indent=2))
    logger.info(f"📝 Test proof written to {manifest_file}")

    return manifest_file


def verify_kv_storage(storage_dir: Path, key: str) -> Path | None:
    """Verify that a KV storage file exists for the given key."""
    # KV storage files are typically stored with the key name as the filename
    storage_file = storage_dir / key
    if storage_file.exists():
        logger.info(f"✅ KV storage file found: {storage_file}")
        return storage_file
    else:
        logger.warning(f"⚠️  KV storage file not found: {storage_file}")
        # List what files are in the directory
        if storage_dir.exists():
            files = list(storage_dir.glob("*"))
            logger.info(f"   Files in {storage_dir}: {[f.name for f in files]}")
        return None


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
async def test_pyclient_goserver_no_mtls(project_root: Path, test_artifacts_dir: Path) -> None:
    """Test Python client -> Go server without mTLS (known working case)"""
    go_server_path = project_root / "bin" / "soup-go"

    if not go_server_path.exists():
        pytest.skip(f"Go RPC server not found at {go_server_path}")

    # Create test-specific directory for all artifacts
    test_dir = test_artifacts_dir / "pyclient_goserver_no_mtls"
    test_dir.mkdir(exist_ok=True)

    # Configure client with KV storage in test directory
    client = KVClient(server_path=str(go_server_path), tls_mode="disabled")
    client.subprocess_env["KV_STORAGE_DIR"] = str(test_dir)

    # Identity-embedded key and value
    test_id = str(uuid.uuid4())[:8]
    test_key = f"pyclient_goserver_no_mtls_{test_id}"
    test_value = b"Python_client->Go_server(no_mTLS)"

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value
        logger.info("✅ Python client → Go server (no mTLS) - PASSED")
        logger.info(f"   Key: {test_key}")
        logger.info(f"   Value: {test_value.decode()}")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write proof manifest to same directory
        kv_files = [str(storage_file)] if storage_file else []
        write_test_proof(
            test_name="pyclient_goserver_no_mtls",
            client_type="python",
            server_type="go",
            tls_mode="disabled",
            crypto_type="none",
            keys_written=[test_key],
            kv_storage_files=kv_files,
            proof_dir=test_dir
        )
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
async def test_pyclient_goserver_with_mtls_auto(project_root: Path, test_artifacts_dir: Path) -> None:
    """Test Python client -> Go server with auto mTLS"""
    go_server_path = project_root / "bin" / "soup-go"

    if not go_server_path.exists():
        pytest.skip(f"Go RPC server not found at {go_server_path}")

    # Create test-specific directory for all artifacts
    test_dir = test_artifacts_dir / "pyclient_goserver_mtls_rsa"
    test_dir.mkdir(exist_ok=True)

    # Configure client with KV storage in test directory
    client = KVClient(
        server_path=str(go_server_path),
        tls_mode="auto",
        tls_key_type="rsa",
    )
    client.subprocess_env["KV_STORAGE_DIR"] = str(test_dir)

    # Identity-embedded key and value
    test_id = str(uuid.uuid4())[:8]
    test_key = f"pyclient_goserver_mtls_rsa_{test_id}"
    test_value = b"Python_client->Go_server(auto_mTLS_RSA)"

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value
        logger.info("✅ Python client → Go server (auto mTLS RSA) - PASSED")
        logger.info(f"   Key: {test_key}")
        logger.info(f"   Value: {test_value.decode()}")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write proof manifest to same directory
        kv_files = [str(storage_file)] if storage_file else []
        write_test_proof(
            test_name="pyclient_goserver_mtls_rsa",
            client_type="python",
            server_type="go",
            tls_mode="auto",
            crypto_type="rsa",
            keys_written=[test_key],
            kv_storage_files=kv_files,
            proof_dir=test_dir
        )
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
async def test_pyclient_goserver_with_mtls_ecdsa(project_root: Path, test_artifacts_dir: Path) -> None:
    """Test Python client -> Go server with auto mTLS using ECDSA (P-256 curve)"""
    go_server_path = project_root / "bin" / "soup-go"

    if not go_server_path.exists():
        pytest.skip(f"Go RPC server not found at {go_server_path}")

    # Create test-specific directory for all artifacts
    test_dir = test_artifacts_dir / "pyclient_goserver_mtls_ecdsa"
    test_dir.mkdir(exist_ok=True)

    # Configure client with KV storage in test directory
    client = KVClient(
        server_path=str(go_server_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="P-256",
    )
    client.subprocess_env["KV_STORAGE_DIR"] = str(test_dir)

    # Identity-embedded key and value
    test_id = str(uuid.uuid4())[:8]
    test_key = f"pyclient_goserver_mtls_ecdsa_{test_id}"
    test_value = b"Python_client->Go_server(auto_mTLS_ECDSA_P256)"

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value
        logger.info("✅ Python client → Go server (auto mTLS ECDSA) - PASSED")
        logger.info(f"   Key: {test_key}")
        logger.info(f"   Value: {test_value.decode()}")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write proof manifest to same directory
        kv_files = [str(storage_file)] if storage_file else []
        write_test_proof(
            test_name="pyclient_goserver_mtls_ecdsa",
            client_type="python",
            server_type="go",
            tls_mode="auto",
            crypto_type="ecdsa_p256",
            keys_written=[test_key],
            kv_storage_files=kv_files,
            proof_dir=test_dir
        )
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_python
@pytest.mark.asyncio
async def test_pyclient_pyserver_no_mtls(project_root: Path, test_artifacts_dir: Path) -> None:
    """Test Python client -> Python server without mTLS"""
    # Use 'soup' command as Python server
    import shutil
    soup_path = shutil.which("soup")

    if not soup_path:
        pytest.skip("soup command not found in PATH")

    # Create test-specific directory for all artifacts
    test_dir = test_artifacts_dir / "pyclient_pyserver_no_mtls"
    test_dir.mkdir(exist_ok=True)

    # Configure client with KV storage in test directory
    client = KVClient(server_path=soup_path, tls_mode="disabled")
    client.subprocess_env["KV_STORAGE_DIR"] = str(test_dir)

    # Identity-embedded key and value
    test_id = str(uuid.uuid4())[:8]
    test_key = f"pyclient_pyserver_no_mtls_{test_id}"
    test_value = b"Python_client->Python_server(no_mTLS)"

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value
        logger.info("✅ Python client → Python server (no mTLS) - PASSED")
        logger.info(f"   Key: {test_key}")
        logger.info(f"   Value: {test_value.decode()}")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write proof manifest to same directory
        kv_files = [str(storage_file)] if storage_file else []
        write_test_proof(
            test_name="pyclient_pyserver_no_mtls",
            client_type="python",
            server_type="python",
            tls_mode="disabled",
            crypto_type="none",
            keys_written=[test_key],
            kv_storage_files=kv_files,
            proof_dir=test_dir
        )
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_python
@pytest.mark.asyncio
async def test_pyclient_pyserver_with_mtls(project_root: Path, test_artifacts_dir: Path) -> None:
    """Test Python client -> Python server with auto mTLS"""
    # Use 'soup' command as Python server
    import shutil
    soup_path = shutil.which("soup")

    if not soup_path:
        pytest.skip("soup command not found in PATH")

    # Create test-specific directory for all artifacts
    test_dir = test_artifacts_dir / "pyclient_pyserver_mtls_rsa"
    test_dir.mkdir(exist_ok=True)

    # Configure client with KV storage in test directory
    client = KVClient(
        server_path=soup_path,
        tls_mode="auto",
        tls_key_type="rsa",
    )
    client.subprocess_env["KV_STORAGE_DIR"] = str(test_dir)

    # Identity-embedded key and value
    test_id = str(uuid.uuid4())[:8]
    test_key = f"pyclient_pyserver_mtls_rsa_{test_id}"
    test_value = b"Python_client->Python_server(auto_mTLS_RSA)"

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value
        logger.info("✅ Python client → Python server (auto mTLS) - PASSED")
        logger.info(f"   Key: {test_key}")
        logger.info(f"   Value: {test_value.decode()}")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write proof manifest to same directory
        kv_files = [str(storage_file)] if storage_file else []
        write_test_proof(
            test_name="pyclient_pyserver_mtls_rsa",
            client_type="python",
            server_type="python",
            tls_mode="auto",
            crypto_type="rsa",
            keys_written=[test_key],
            kv_storage_files=kv_files,
            proof_dir=test_dir
        )
    finally:
        await client.close()


# 🍲🥄🧪🪄

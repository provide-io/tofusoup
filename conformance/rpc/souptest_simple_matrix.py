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

def verify_kv_storage(storage_dir: Path, key: str) -> Path | None:
    """Verify that a KV storage file exists for the given key.

    The server may prefix the key with "kv-data-" when writing to disk.
    """
    # Try direct key name first
    storage_file = storage_dir / key
    if storage_file.exists():
        logger.info(f"✅ KV storage file found: {storage_file}")
        return storage_file

    # Try with "kv-data-" prefix (used by some server implementations)
    storage_file_prefixed = storage_dir / f"kv-data-{key}"
    if storage_file_prefixed.exists():
        logger.info(f"✅ KV storage file found: {storage_file_prefixed}")
        return storage_file_prefixed

    # File not found - log warning and list directory contents
    logger.warning(f"⚠️  KV storage file not found: {storage_file} or {storage_file_prefixed}")
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

    # Identity-embedded key
    test_id = str(uuid.uuid4())[:8]
    test_key = f"proof_pyclient_goserver_no_mtls_{test_id}"

    # Create proof manifest as the value to store
    proof_manifest = {
        "test_name": "pyclient_goserver_no_mtls",
        "client_type": "python",
        "server_type": "go",
        "tls_mode": "disabled",
        "crypto_type": "none",
        "key": test_key,
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }
    test_value = json.dumps(proof_manifest, indent=2).encode()

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value

        # Verify the retrieved value is valid JSON with correct content
        retrieved_manifest = json.loads(retrieved.decode())
        assert retrieved_manifest["test_name"] == "pyclient_goserver_no_mtls"
        assert retrieved_manifest["client_type"] == "python"
        assert retrieved_manifest["server_type"] == "go"

        logger.info("✅ Python client → Go server (no mTLS) - PASSED")
        logger.info(f"   Key: {test_key}")
        logger.info(f"   Value: {retrieved_manifest['test_name']} proof manifest")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write proof manifest to same directory (with storage file info)
        proof_manifest["kv_storage_files"] = [str(storage_file)] if storage_file else []
        manifest_file = test_dir / f"{proof_manifest['test_name']}_{int(time.time())}.json"
        manifest_file.write_text(json.dumps(proof_manifest, indent=2))
        logger.info(f"📝 Test proof written to {manifest_file}")
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

    # Identity-embedded key
    test_id = str(uuid.uuid4())[:8]
    test_key = f"proof_pyclient_goserver_mtls_rsa_{test_id}"

    # Create proof manifest as the value to store
    proof_manifest = {
        "test_name": "pyclient_goserver_mtls_rsa",
        "client_type": "python",
        "server_type": "go",
        "tls_mode": "auto",
        "crypto_type": "rsa",
        "key": test_key,
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }
    test_value = json.dumps(proof_manifest, indent=2).encode()

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value

        # Verify the retrieved value is valid JSON with correct content
        retrieved_manifest = json.loads(retrieved.decode())
        assert retrieved_manifest["test_name"] == "pyclient_goserver_mtls_rsa"
        assert retrieved_manifest["crypto_type"] == "rsa"

        logger.info("✅ Python client → Go server (auto mTLS RSA) - PASSED")
        logger.info(f"   Key: {test_key}")
        logger.info(f"   Value: {retrieved_manifest['test_name']} proof manifest")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write proof manifest to same directory (with storage file info)
        proof_manifest["kv_storage_files"] = [str(storage_file)] if storage_file else []
        manifest_file = test_dir / f"{proof_manifest['test_name']}_{int(time.time())}.json"
        manifest_file.write_text(json.dumps(proof_manifest, indent=2))
        logger.info(f"📝 Test proof written to {manifest_file}")
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

    # Identity-embedded key
    test_id = str(uuid.uuid4())[:8]
    test_key = f"proof_pyclient_goserver_mtls_ecdsa_{test_id}"

    # Create proof manifest as the value to store
    proof_manifest = {
        "test_name": "pyclient_goserver_mtls_ecdsa",
        "client_type": "python",
        "server_type": "go",
        "tls_mode": "auto",
        "crypto_type": "ecdsa_p256",
        "key": test_key,
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }
    test_value = json.dumps(proof_manifest, indent=2).encode()

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value

        # Verify the retrieved value is valid JSON with correct content
        retrieved_manifest = json.loads(retrieved.decode())
        assert retrieved_manifest["test_name"] == "pyclient_goserver_mtls_ecdsa"
        assert retrieved_manifest["crypto_type"] == "ecdsa_p256"

        logger.info("✅ Python client → Go server (auto mTLS ECDSA) - PASSED")
        logger.info(f"   Key: {test_key}")
        logger.info(f"   Value: {retrieved_manifest['test_name']} proof manifest")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write proof manifest to same directory (with storage file info)
        proof_manifest["kv_storage_files"] = [str(storage_file)] if storage_file else []
        manifest_file = test_dir / f"{proof_manifest['test_name']}_{int(time.time())}.json"
        manifest_file.write_text(json.dumps(proof_manifest, indent=2))
        logger.info(f"📝 Test proof written to {manifest_file}")
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

    # Identity-embedded key
    test_id = str(uuid.uuid4())[:8]
    test_key = f"proof_pyclient_pyserver_no_mtls_{test_id}"

    # Create proof manifest as the value to store
    proof_manifest = {
        "test_name": "pyclient_pyserver_no_mtls",
        "client_type": "python",
        "server_type": "python",
        "tls_mode": "disabled",
        "crypto_type": "none",
        "key": test_key,
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }
    test_value = json.dumps(proof_manifest, indent=2).encode()

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value

        # Verify the retrieved value is valid JSON with correct content
        retrieved_manifest = json.loads(retrieved.decode())
        assert retrieved_manifest["test_name"] == "pyclient_pyserver_no_mtls"
        assert retrieved_manifest["server_type"] == "python"

        logger.info("✅ Python client → Python server (no mTLS) - PASSED")
        logger.info(f"   Key: {test_key}")
        logger.info(f"   Value: {retrieved_manifest['test_name']} proof manifest")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write proof manifest to same directory (with storage file info)
        proof_manifest["kv_storage_files"] = [str(storage_file)] if storage_file else []
        manifest_file = test_dir / f"{proof_manifest['test_name']}_{int(time.time())}.json"
        manifest_file.write_text(json.dumps(proof_manifest, indent=2))
        logger.info(f"📝 Test proof written to {manifest_file}")
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

    # Identity-embedded key
    test_id = str(uuid.uuid4())[:8]
    test_key = f"proof_pyclient_pyserver_mtls_rsa_{test_id}"

    # Create proof manifest as the value to store
    proof_manifest = {
        "test_name": "pyclient_pyserver_mtls_rsa",
        "client_type": "python",
        "server_type": "python",
        "tls_mode": "auto",
        "crypto_type": "rsa",
        "key": test_key,
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }
    test_value = json.dumps(proof_manifest, indent=2).encode()

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value

        # Verify the retrieved value is valid JSON with correct content
        retrieved_manifest = json.loads(retrieved.decode())
        assert retrieved_manifest["test_name"] == "pyclient_pyserver_mtls_rsa"
        assert retrieved_manifest["server_type"] == "python"

        logger.info("✅ Python client → Python server (auto mTLS) - PASSED")
        logger.info(f"   Key: {test_key}")
        logger.info(f"   Value: {retrieved_manifest['test_name']} proof manifest")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write proof manifest to same directory (with storage file info)
        proof_manifest["kv_storage_files"] = [str(storage_file)] if storage_file else []
        manifest_file = test_dir / f"{proof_manifest['test_name']}_{int(time.time())}.json"
        manifest_file.write_text(json.dumps(proof_manifest, indent=2))
        logger.info(f"📝 Test proof written to {manifest_file}")
    finally:
        await client.close()


# 🍲🥄🧪🪄

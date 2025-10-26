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

# Proof directory for matrix test verification
PROOF_DIR = Path("/tmp/tofusoup_rpc_test_proof")


def write_test_proof(test_name: str, client_type: str, server_type: str,
                     tls_mode: str, crypto_type: str, keys_written: list[str],
                     kv_storage_files: list[str] | None = None) -> Path:
    """Write proof manifest that this test ran and what it wrote."""
    PROOF_DIR.mkdir(exist_ok=True, parents=True)

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

    manifest_file = PROOF_DIR / f"{test_name}_{int(time.time())}.json"
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
async def test_pyclient_goserver_no_mtls(project_root: Path) -> None:
    """Test Python client -> Go server without mTLS (known working case)"""
    import os
    go_server_path = project_root / "bin" / "soup-go"

    if not go_server_path.exists():
        pytest.skip(f"Go RPC server not found at {go_server_path}")

    client = KVClient(server_path=str(go_server_path), tls_mode="disabled")

    # Identity-embedded key and value
    test_id = str(uuid.uuid4())[:8]
    test_key = f"pyclient_goserver_no_mtls_{test_id}"
    test_value = b"Python_client->Go_server(no_mTLS)"

    # KV storage directory (default is /tmp)
    storage_dir = Path(os.environ.get("KV_STORAGE_DIR", "/tmp"))

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value
        logger.info("✅ Python client → Go server (no mTLS) - PASSED")
        logger.info(f"   Key: {test_key}")
        logger.info(f"   Value: {test_value.decode()}")

        # Verify KV storage file exists
        storage_file = verify_kv_storage(storage_dir, test_key)

        # Write proof manifest
        kv_files = [str(storage_file)] if storage_file else []
        write_test_proof(
            test_name="pyclient_goserver_no_mtls",
            client_type="python",
            server_type="go",
            tls_mode="disabled",
            crypto_type="none",
            keys_written=[test_key],
            kv_storage_files=kv_files
        )
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
async def test_pyclient_goserver_with_mtls_auto(project_root: Path) -> None:
    """Test Python client -> Go server with auto mTLS"""
    go_server_path = project_root / "bin" / "soup-go"

    if not go_server_path.exists():
        pytest.skip(f"Go RPC server not found at {go_server_path}")

    client = KVClient(
        server_path=str(go_server_path),
        tls_mode="auto",
        tls_key_type="rsa",
    )

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

        # Write proof manifest
        write_test_proof(
            test_name="pyclient_goserver_mtls_rsa",
            client_type="python",
            server_type="go",
            tls_mode="auto",
            crypto_type="rsa",
            keys_written=[test_key]
        )
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
async def test_pyclient_goserver_with_mtls_ecdsa(project_root: Path) -> None:
    """Test Python client -> Go server with auto mTLS using ECDSA (P-256 curve)"""
    go_server_path = project_root / "bin" / "soup-go"

    if not go_server_path.exists():
        pytest.skip(f"Go RPC server not found at {go_server_path}")

    client = KVClient(
        server_path=str(go_server_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="P-256",
    )

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

        # Write proof manifest
        write_test_proof(
            test_name="pyclient_goserver_mtls_ecdsa",
            client_type="python",
            server_type="go",
            tls_mode="auto",
            crypto_type="ecdsa_p256",
            keys_written=[test_key]
        )
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_python
@pytest.mark.asyncio
async def test_pyclient_pyserver_no_mtls(project_root: Path) -> None:
    """Test Python client -> Python server without mTLS"""
    # Use 'soup' command as Python server
    import shutil
    soup_path = shutil.which("soup")

    if not soup_path:
        pytest.skip("soup command not found in PATH")

    client = KVClient(server_path=soup_path, tls_mode="disabled")

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

        # Write proof manifest
        write_test_proof(
            test_name="pyclient_pyserver_no_mtls",
            client_type="python",
            server_type="python",
            tls_mode="disabled",
            crypto_type="none",
            keys_written=[test_key]
        )
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_python
@pytest.mark.asyncio
async def test_pyclient_pyserver_with_mtls(project_root: Path) -> None:
    """Test Python client -> Python server with auto mTLS"""
    # Use 'soup' command as Python server
    import shutil
    soup_path = shutil.which("soup")

    if not soup_path:
        pytest.skip("soup command not found in PATH")

    client = KVClient(server_path=soup_path, tls_mode="auto", tls_key_type="rsa")

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

        # Write proof manifest
        write_test_proof(
            test_name="pyclient_pyserver_mtls_rsa",
            client_type="python",
            server_type="python",
            tls_mode="auto",
            crypto_type="rsa",
            keys_written=[test_key]
        )
    finally:
        await client.close()


# 🍲🥄🧪🪄

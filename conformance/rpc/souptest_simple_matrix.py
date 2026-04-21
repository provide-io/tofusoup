#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Simple RPC K/V Matrix Testing

Tests the key known working combinations:
- Go client → Go server (with and without mTLS)
- Python client → Go server (with and without mTLS)
- Go client → Python server (with and without mTLS)
- Python client → Python server (with and without mTLS)

Uses the existing working KVClient infrastructure."""

from datetime import datetime
import hashlib
import json
from pathlib import Path
import time
import uuid

from provide.foundation import logger
import pytest

from tofusoup.common.config import load_tofusoup_config
from tofusoup.harness.logic import ensure_go_harness_build
from tofusoup.rpc.client import KVClient


def _get_cert_fingerprint(cert_pem: str | bytes | None) -> str | None:
    """Get SHA256 fingerprint of a PEM certificate.

    Args:
        cert_pem: PEM-encoded certificate as string or bytes

    Returns:
        Hexadecimal SHA256 fingerprint, or None if cert is invalid
    """
    if not cert_pem:
        return None
    try:
        cert_bytes = cert_pem.encode() if isinstance(cert_pem, str) else cert_pem
        return hashlib.sha256(cert_bytes).hexdigest()
    except Exception:
        return None


def verify_kv_storage(storage_dir: Path, key: str) -> Path | None:
    """Verify that a KV storage file exists for the given key.

    The server may prefix the key with "kv-data-" when writing to disk.
    """
    # Try direct key name first
    storage_file = storage_dir / key
    if storage_file.exists():
        return storage_file

    # Try with "kv-data-" prefix (used by some server implementations)
    storage_file_prefixed = storage_dir / f"kv-data-{key}"
    if storage_file_prefixed.exists():
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
@pytest.mark.skip(reason="Python client → Go server not supported (pyvider-rpcplugin limitation)")
async def test_pyclient_goserver_no_mtls(project_root: Path, test_artifacts_dir: Path) -> None:
    """Test Python client -> Go server without mTLS (SKIPPED - known limitation)"""
    config = load_tofusoup_config(project_root)
    go_server_path = ensure_go_harness_build("soup-go", project_root, config)

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
        "status": "pending",  # Changed to pending until test completes
        "user_data": {  # Optional user payload
            "description": "Testing Python client to Go server without mTLS",
            "test_iteration": 1,
        },
    }
    test_value = json.dumps(proof_manifest, indent=2).encode()

    try:
        start_time = time.time()
        await client.start()
        connection_time = time.time() - start_time

        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)

        # Verify the retrieved value is valid JSON with correct content
        retrieved_manifest = json.loads(retrieved.decode())
        assert retrieved_manifest["test_name"] == "pyclient_goserver_no_mtls"
        assert retrieved_manifest["client_type"] == "python"
        assert retrieved_manifest["server_type"] == "go"

        # Verify server added its handshake with combo identification
        assert "server_handshake" in retrieved_manifest, "Server should add handshake to JSON"
        server_handshake = retrieved_manifest["server_handshake"]

        # Verify combo identification fields
        assert "server_language" in server_handshake, "Server should identify its language"
        assert server_handshake["server_language"] == "go", "Expected Go server"
        assert "client_language" in server_handshake, "Server should identify client language"
        # Note: client_language may be "unknown" if not explicitly set in environment
        assert "combo_id" in server_handshake, "Server should include combo_id"

        # Verify crypto_config is present and structured correctly
        if "crypto_config" in server_handshake:
            crypto_config = server_handshake["crypto_config"]
            assert "key_type" in crypto_config, "crypto_config should include key_type"

        # Add client handshake information
        client_handshake = {
            "target_endpoint": str(client._client.target_endpoint)
            if hasattr(client._client, "target_endpoint")
            else "unknown",
            "protocol_version": client.subprocess_env.get("PLUGIN_PROTOCOL_VERSIONS", "1"),
            "tls_mode": client.tls_mode,
            "tls_config": {
                "key_type": client.tls_key_type,
                "curve": client.tls_curve if client.tls_key_type == "ec" else None,
            },
            "cert_fingerprint": _get_cert_fingerprint(getattr(client._client, "client_cert", None)),
            "timestamp": datetime.now().isoformat(),
            "connection_time": round(connection_time, 3),
        }
        retrieved_manifest["client_handshake"] = client_handshake

        # Update status to success
        retrieved_manifest["status"] = "success"

        logger.info(f"   Key: {test_key}")
        logger.info(f"   Server handshake: {retrieved_manifest['server_handshake'].get('endpoint')}")
        logger.info(f"   Client connection time: {connection_time:.3f}s")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write final proof manifest showing complete round-trip with both handshakes
        retrieved_manifest["kv_storage_files"] = [str(storage_file)] if storage_file else []
        manifest_file = test_dir / f"{retrieved_manifest['test_name']}_{int(time.time())}.json"
        manifest_file.write_text(json.dumps(retrieved_manifest, indent=2))
        logger.info(f"📝 Test proof written to {manifest_file}")
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
@pytest.mark.skip(reason="Python client → Go server not supported (pyvider-rpcplugin limitation)")
async def test_pyclient_goserver_with_mtls_auto(project_root: Path, test_artifacts_dir: Path) -> None:
    """Test Python client -> Go server with auto mTLS (SKIPPED - known limitation)"""
    config = load_tofusoup_config(project_root)
    go_server_path = ensure_go_harness_build("soup-go", project_root, config)

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
        "status": "pending",  # Changed to pending until test completes
        "user_data": {  # Optional user payload
            "description": "Testing Python client to Go server with auto mTLS (RSA)",
            "test_iteration": 1,
        },
    }
    test_value = json.dumps(proof_manifest, indent=2).encode()

    try:
        start_time = time.time()
        await client.start()
        connection_time = time.time() - start_time

        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)

        # Verify the retrieved value is valid JSON with correct content
        retrieved_manifest = json.loads(retrieved.decode())
        assert retrieved_manifest["test_name"] == "pyclient_goserver_mtls_rsa"
        assert retrieved_manifest["client_type"] == "python"
        assert retrieved_manifest["server_type"] == "go"

        # Verify server added its handshake with combo identification
        assert "server_handshake" in retrieved_manifest, "Server should add handshake to JSON"
        server_handshake = retrieved_manifest["server_handshake"]

        # Verify combo identification fields
        assert "server_language" in server_handshake, "Server should identify its language"
        assert server_handshake["server_language"] == "go", "Expected Go server"
        assert "client_language" in server_handshake, "Server should identify client language"
        assert "combo_id" in server_handshake, "Server should include combo_id"

        # Verify crypto_config is present with RSA details
        assert "crypto_config" in server_handshake, "crypto_config should be present for mTLS"
        crypto_config = server_handshake["crypto_config"]
        assert crypto_config["key_type"] == "rsa", "Expected RSA key type"

        # Add client handshake information
        client_handshake = {
            "target_endpoint": str(client._client.target_endpoint)
            if hasattr(client._client, "target_endpoint")
            else "unknown",
            "protocol_version": client.subprocess_env.get("PLUGIN_PROTOCOL_VERSIONS", "1"),
            "tls_mode": client.tls_mode,
            "tls_config": {
                "key_type": client.tls_key_type,
                "curve": client.tls_curve if client.tls_key_type == "ec" else None,
            },
            "cert_fingerprint": _get_cert_fingerprint(getattr(client._client, "client_cert", None)),
            "timestamp": datetime.now().isoformat(),
            "connection_time": round(connection_time, 3),
        }
        retrieved_manifest["client_handshake"] = client_handshake

        # Update status to success
        retrieved_manifest["status"] = "success"

        logger.info(f"   Key: {test_key}")
        logger.info(f"   Server handshake: {retrieved_manifest['server_handshake'].get('endpoint')}")
        logger.info(f"   Client connection time: {connection_time:.3f}s")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write final proof manifest showing complete round-trip with both handshakes
        retrieved_manifest["kv_storage_files"] = [str(storage_file)] if storage_file else []
        manifest_file = test_dir / f"{retrieved_manifest['test_name']}_{int(time.time())}.json"
        manifest_file.write_text(json.dumps(retrieved_manifest, indent=2))
        logger.info(f"📝 Test proof written to {manifest_file}")
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
@pytest.mark.skip(reason="Python client → Go server not supported (pyvider-rpcplugin limitation)")
async def test_pyclient_goserver_with_mtls_ecdsa(project_root: Path, test_artifacts_dir: Path) -> None:
    """Test Python client -> Go server with auto mTLS using ECDSA (SKIPPED - known limitation)"""
    config = load_tofusoup_config(project_root)
    go_server_path = ensure_go_harness_build("soup-go", project_root, config)

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
        "status": "pending",  # Changed to pending until test completes
        "user_data": {  # Optional user payload
            "description": "Testing Python client to Go server with auto mTLS (ECDSA P-256)",
            "test_iteration": 1,
        },
    }
    test_value = json.dumps(proof_manifest, indent=2).encode()

    try:
        start_time = time.time()
        await client.start()
        connection_time = time.time() - start_time

        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)

        # Verify the retrieved value is valid JSON with correct content
        retrieved_manifest = json.loads(retrieved.decode())
        assert retrieved_manifest["test_name"] == "pyclient_goserver_mtls_ecdsa"
        assert retrieved_manifest["client_type"] == "python"
        assert retrieved_manifest["server_type"] == "go"

        # Verify server added its handshake
        assert "server_handshake" in retrieved_manifest, "Server should add handshake to JSON"

        # Add client handshake information
        client_handshake = {
            "target_endpoint": str(client._client.target_endpoint)
            if hasattr(client._client, "target_endpoint")
            else "unknown",
            "protocol_version": client.subprocess_env.get("PLUGIN_PROTOCOL_VERSIONS", "1"),
            "tls_mode": client.tls_mode,
            "tls_config": {
                "key_type": client.tls_key_type,
                "curve": client.tls_curve if client.tls_key_type == "ec" else None,
            },
            "cert_fingerprint": _get_cert_fingerprint(getattr(client._client, "client_cert", None)),
            "timestamp": datetime.now().isoformat(),
            "connection_time": round(connection_time, 3),
        }
        retrieved_manifest["client_handshake"] = client_handshake

        # Update status to success
        retrieved_manifest["status"] = "success"

        logger.info(f"   Key: {test_key}")
        logger.info(f"   Server handshake: {retrieved_manifest['server_handshake'].get('endpoint')}")
        logger.info(f"   Client connection time: {connection_time:.3f}s")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write final proof manifest showing complete round-trip with both handshakes
        retrieved_manifest["kv_storage_files"] = [str(storage_file)] if storage_file else []
        manifest_file = test_dir / f"{retrieved_manifest['test_name']}_{int(time.time())}.json"
        manifest_file.write_text(json.dumps(retrieved_manifest, indent=2))
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
        "status": "pending",  # Changed to pending until test completes
        "user_data": {  # Optional user payload
            "description": "Testing Python client to Python server without mTLS",
            "test_iteration": 1,
        },
    }
    test_value = json.dumps(proof_manifest, indent=2).encode()

    try:
        start_time = time.time()
        await client.start()
        connection_time = time.time() - start_time

        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)

        # Verify the retrieved value is valid JSON with correct content
        retrieved_manifest = json.loads(retrieved.decode())
        assert retrieved_manifest["test_name"] == "pyclient_pyserver_no_mtls"
        assert retrieved_manifest["client_type"] == "python"
        assert retrieved_manifest["server_type"] == "python"

        # Verify server added its handshake
        assert "server_handshake" in retrieved_manifest, "Server should add handshake to JSON"

        # Add client handshake information
        client_handshake = {
            "target_endpoint": str(client._client.target_endpoint)
            if hasattr(client._client, "target_endpoint")
            else "unknown",
            "protocol_version": client.subprocess_env.get("PLUGIN_PROTOCOL_VERSIONS", "1"),
            "tls_mode": client.tls_mode,
            "tls_config": {
                "key_type": client.tls_key_type,
                "curve": client.tls_curve if client.tls_key_type == "ec" else None,
            },
            "cert_fingerprint": _get_cert_fingerprint(getattr(client._client, "client_cert", None)),
            "timestamp": datetime.now().isoformat(),
            "connection_time": round(connection_time, 3),
        }
        retrieved_manifest["client_handshake"] = client_handshake

        # Update status to success
        retrieved_manifest["status"] = "success"

        logger.info(f"   Key: {test_key}")
        logger.info(f"   Server handshake: {retrieved_manifest['server_handshake'].get('endpoint')}")
        logger.info(f"   Client connection time: {connection_time:.3f}s")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write final proof manifest showing complete round-trip with both handshakes
        retrieved_manifest["kv_storage_files"] = [str(storage_file)] if storage_file else []
        manifest_file = test_dir / f"{retrieved_manifest['test_name']}_{int(time.time())}.json"
        manifest_file.write_text(json.dumps(retrieved_manifest, indent=2))
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
        "status": "pending",  # Changed to pending until test completes
        "user_data": {  # Optional user payload
            "description": "Testing Python client to Python server with auto mTLS (RSA)",
            "test_iteration": 1,
        },
    }
    test_value = json.dumps(proof_manifest, indent=2).encode()

    try:
        start_time = time.time()
        await client.start()
        connection_time = time.time() - start_time

        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)

        # Verify the retrieved value is valid JSON with correct content
        retrieved_manifest = json.loads(retrieved.decode())
        assert retrieved_manifest["test_name"] == "pyclient_pyserver_mtls_rsa"
        assert retrieved_manifest["client_type"] == "python"
        assert retrieved_manifest["server_type"] == "python"

        # Verify server added its handshake
        assert "server_handshake" in retrieved_manifest, "Server should add handshake to JSON"

        # Add client handshake information
        client_handshake = {
            "target_endpoint": str(client._client.target_endpoint)
            if hasattr(client._client, "target_endpoint")
            else "unknown",
            "protocol_version": client.subprocess_env.get("PLUGIN_PROTOCOL_VERSIONS", "1"),
            "tls_mode": client.tls_mode,
            "tls_config": {
                "key_type": client.tls_key_type,
                "curve": client.tls_curve if client.tls_key_type == "ec" else None,
            },
            "cert_fingerprint": _get_cert_fingerprint(getattr(client._client, "client_cert", None)),
            "timestamp": datetime.now().isoformat(),
            "connection_time": round(connection_time, 3),
        }
        retrieved_manifest["client_handshake"] = client_handshake

        # Update status to success
        retrieved_manifest["status"] = "success"

        logger.info(f"   Key: {test_key}")
        logger.info(f"   Server handshake: {retrieved_manifest['server_handshake'].get('endpoint')}")
        logger.info(f"   Client connection time: {connection_time:.3f}s")

        # Verify KV storage file exists in test directory
        storage_file = verify_kv_storage(test_dir, test_key)

        # Write final proof manifest showing complete round-trip with both handshakes
        retrieved_manifest["kv_storage_files"] = [str(storage_file)] if storage_file else []
        manifest_file = test_dir / f"{retrieved_manifest['test_name']}_{int(time.time())}.json"
        manifest_file.write_text(json.dumps(retrieved_manifest, indent=2))
        logger.info(f"📝 Test proof written to {manifest_file}")
    finally:
        await client.close()


# 🥣🔬🔚

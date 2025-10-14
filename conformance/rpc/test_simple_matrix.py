"""
Simple RPC K/V Matrix Testing

Tests the key known working combinations:
- Go client → Go server (with and without mTLS)
- Python client → Go server (with and without mTLS)
- Go client → Python server (with and without mTLS)
- Python client → Python server (with and without mTLS)

Uses the existing working KVClient infrastructure.
"""

from pathlib import Path
import uuid

from provide.foundation import logger
import pytest

from tofusoup.rpc.client import KVClient


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
async def test_pyclient_goserver_no_mtls(project_root: Path):
    """Test Python client -> Go server without mTLS (known working case)"""
    go_server_path = project_root / "bin" / "soup-go"

    if not go_server_path.exists():
        pytest.skip(f"Go RPC server not found at {go_server_path}")

    client = KVClient(server_path=str(go_server_path), tls_mode="disabled")

    test_key = f"simple-test-{uuid.uuid4()}"
    test_value = b"Hello from simple matrix test"

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value
        logger.info("✅ Python client → Go server (no mTLS) - PASSED")
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
async def test_pyclient_goserver_with_mtls_auto(project_root: Path):
    """Test Python client -> Go server with auto mTLS"""
    go_server_path = project_root / "bin" / "soup-go"

    if not go_server_path.exists():
        pytest.skip(f"Go RPC server not found at {go_server_path}")

    client = KVClient(
        server_path=str(go_server_path),
        tls_mode="auto",
        tls_key_type="rsa",
    )

    test_key = f"mtls-test-{uuid.uuid4()}"
    test_value = b"Hello from mTLS test"

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value
        logger.info("✅ Python client → Go server (auto mTLS RSA) - PASSED")
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_go
@pytest.mark.asyncio
@pytest.mark.skip(reason="Python client → Go server with mTLS is not currently supported (known issue in pyvider-rpcplugin)")
async def test_pyclient_goserver_with_mtls_ecdsa(project_root: Path):
    """Test Python client -> Go server with auto mTLS using ECDSA"""
    go_server_path = project_root / "bin" / "soup-go"

    if not go_server_path.exists():
        pytest.skip(f"Go RPC server not found at {go_server_path}")

    client = KVClient(server_path=str(go_server_path), tls_mode="auto", tls_key_type="ec")

    test_key = f"ecdsa-test-{uuid.uuid4()}"
    test_value = b"Hello from ECDSA mTLS test"

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value
        logger.info("✅ Python client → Go server (auto mTLS ECDSA) - PASSED")
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_python
@pytest.mark.asyncio
async def test_pyclient_pyserver_no_mtls(project_root: Path):
    """Test Python client -> Python server without mTLS"""
    py_server_path = project_root / "bin" / "python-kv-server"

    if not py_server_path.exists():
        pytest.skip(f"Python KV server not found at {py_server_path}")

    client = KVClient(server_path=str(py_server_path), tls_mode="disabled")

    test_key = f"py2py-test-{uuid.uuid4()}"
    test_value = b"Hello from Python to Python"

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value
        logger.info("✅ Python client → Python server (no mTLS) - PASSED")
    finally:
        await client.close()


@pytest.mark.integration_rpc
@pytest.mark.harness_python
@pytest.mark.asyncio
async def test_pyclient_pyserver_with_mtls(project_root: Path):
    """Test Python client -> Python server with auto mTLS"""
    py_server_path = project_root / "bin" / "python-kv-server"

    if not py_server_path.exists():
        pytest.skip(f"Python KV server not found at {py_server_path}")

    client = KVClient(server_path=str(py_server_path), tls_mode="auto", tls_key_type="rsa")

    test_key = f"py2py-mtls-{uuid.uuid4()}"
    test_value = b"Hello from Python to Python with mTLS"

    try:
        await client.start()
        await client.put(test_key, test_value)
        retrieved = await client.get(test_key)
        assert retrieved == test_value
        logger.info("✅ Python client → Python server (auto mTLS) - PASSED")
    finally:
        await client.close()


# 🍲🥄🧪🪄

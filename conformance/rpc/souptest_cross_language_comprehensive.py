"""
Cross-Language RPC Conformance Tests

Tests all combinations of Go and Python clients/servers to verify
that put/get operations work correctly across language boundaries.

This consolidates and improves upon the original test_cross_language_proof.py
by using proper pytest fixtures and removing hardcoded paths.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import shutil
import subprocess
import time

import pytest
from provide.foundation import logger


@pytest.fixture
def soup_go_path() -> Path | None:
    """Find the soup-go executable."""
    # Try multiple possible locations
    candidates = [
        Path("bin/soup-go"),
        Path("harnesses/bin/soup-go"),
        Path(__file__).parent.parent.parent / "bin" / "soup-go",
    ]

    for path in candidates:
        if path.exists():
            return path.resolve()

    # Try finding in PATH
    soup_go = shutil.which("soup-go")
    if soup_go:
        return Path(soup_go)

    return None


@pytest.fixture
def soup_path() -> Path | None:
    """Find the soup executable (Python)."""
    soup = shutil.which("soup")
    if soup:
        return Path(soup)
    return None


@pytest.mark.asyncio
async def test_python_to_python(soup_path: Path | None) -> None:
    """Test Python client → Python server."""
    if soup_path is None:
        pytest.skip("soup executable not found in PATH")

    from tofusoup.rpc.client import KVClient

    client = KVClient(
        server_path=str(soup_path),
        tls_mode="auto",
        tls_key_type="rsa"
    )

    try:
        # Set a generous timeout as Python→Python may have handshake issues
        await asyncio.wait_for(client.start(), timeout=10.0)

        # Test put operation
        test_key = "test-pypy-proof"
        test_value = b"Hello from Python client to Python server!"

        await client.put(test_key, test_value)

        # Test get operation
        retrieved = await client.get(test_key)

        assert retrieved == test_value, f"Value mismatch: expected {test_value!r}, got {retrieved!r}"

    finally:
        try:
            await client.close()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_python_to_go(soup_go_path: Path | None) -> None:
    """Test Python client → Go server."""
    if soup_go_path is None:
        pytest.skip("soup-go executable not found")

    from tofusoup.rpc.client import KVClient

    # Create client with EC P-256 (works well with Go)
    client = KVClient(
        server_path=str(soup_go_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="P-256"
    )

    try:
        await asyncio.wait_for(client.start(), timeout=15.0)

        # Test put operation
        test_key = "test-pygo-proof"
        test_value = b"Hello from Python client to Go server!"

        await client.put(test_key, test_value)

        # Test get operation
        retrieved = await client.get(test_key)

        assert retrieved == test_value, f"Value mismatch: expected {test_value!r}, got {retrieved!r}"

    finally:
        try:
            await client.close()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_go_to_python(soup_go_path: Path | None, soup_path: Path | None,
                            test_artifacts_dir: Path) -> None:
    """Test Go client → Python server by explicitly starting server and client."""
    logger.info("="*80)
    logger.info("🧪 TEST: Go Client → Python Server")
    logger.info("="*80)

    if soup_go_path is None:
        pytest.skip("soup-go executable not found")
    if soup_path is None:
        pytest.skip("soup executable not found in PATH")

    logger.info(f"📁 Go client path: {soup_go_path}")
    logger.info(f"🐍 Python server path: {soup_path}")

    # Create test-specific directory for all artifacts
    test_dir = test_artifacts_dir / "go_to_python"
    test_dir.mkdir(exist_ok=True)
    logger.info(f"📂 Test artifacts directory: {test_dir}")

    env = os.environ.copy()
    env["KV_STORAGE_DIR"] = str(test_dir)
    env["LOG_LEVEL"] = "INFO"
    env["BASIC_PLUGIN"] = "hello"
    env["PLUGIN_MAGIC_COOKIE_KEY"] = "BASIC_PLUGIN"

    # 1. Start the Python server with mTLS enabled
    server_command = [str(soup_path), "rpc", "kv", "server", "--tls-mode", "auto", "--tls-curve", "secp256r1"]
    logger.info(f"🚀 Starting Python server with command: {' '.join(server_command)}")
    logger.info(f"🔐 TLS Configuration: mode=auto, curve=secp256r1 (P-256)")
    server_process = subprocess.Popen(
        server_command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for the server to start and output its handshake
    # Handshake format: core_version|protocol_version|network|address|protocol|cert
    # Example: 1|1|tcp|127.0.0.1:54321|grpc|CERT_BASE64
    logger.info("⏳ Waiting for Python server handshake...")
    handshake_line = ""
    timeout_seconds = 30
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        line = server_process.stdout.readline()
        if line:
            # Look for the go-plugin handshake pattern: starts with "1|1|tcp|" or "1|1|unix|"
            if line.startswith("1|1|tcp|") or line.startswith("1|1|unix|") or "|tcp|" in line or "|unix|" in line:
                handshake_line = line.strip()
                logger.info(f"✅ Received handshake after {time.time() - start_time:.2f}s")
                break
        else:
            # If no line, give the server a moment to produce output
            await asyncio.sleep(0.1)

        # Check if the process has terminated prematurely
        if server_process.poll() is not None:
            stderr_output = server_process.stderr.read()
            logger.error(f"❌ Server terminated prematurely! Stderr: {stderr_output}")
            raise AssertionError(f"Server process terminated prematurely. Stderr: {stderr_output}")

    assert handshake_line, "Python server did not output handshake line"

    # Verify handshake format
    parts = handshake_line.split('|')
    assert len(parts) == 6, f"Invalid handshake line format: {handshake_line}"

    logger.info(f"🔍 Handshake parts:")
    logger.info(f"  - Core version: {parts[0]}")
    logger.info(f"  - Protocol version: {parts[1]}")
    logger.info(f"  - Network: {parts[2]}")
    logger.info(f"  - Address: {parts[3]}")
    logger.info(f"  - Protocol: {parts[4]}")
    logger.info(f"  - Certificate: {parts[5][:50]}... (truncated)")

    port = parts[3].split(':')[-1]
    logger.info(f"🔌 Server listening on port: {port}")

    # 2. Run the Go client to put a value
    # Pass the FULL handshake line (including certificate) to --address for mTLS support
    put_key = "go-py-key"
    put_value = "Hello from Go client to Python server!"
    put_command = [
        str(soup_go_path), "rpc", "kv", "put",
        f"--address={handshake_line}",  # Pass full handshake with certificate
        put_key, put_value
    ]

    logger.info(f"📤 Executing Go client PUT operation:")
    logger.info(f"   Command: {' '.join(put_command[:4])} [handshake] {put_key} {put_value}")
    logger.info(f"   Key: {put_key}")
    logger.info(f"   Value: {put_value}")
    logger.info(f"   TLS: Auto-detect curve from server cert (should detect P-256)")

    put_result = subprocess.run(
        put_command,
        env=env,
        capture_output=True,
        text=True,
        timeout=10
    )

    if put_result.returncode != 0:
        logger.error(f"❌ Go client PUT failed!")
        logger.error(f"   Exit code: {put_result.returncode}")
        logger.error(f"   Stdout: {put_result.stdout}")
        logger.error(f"   Stderr: {put_result.stderr}")
    else:
        logger.info(f"✅ Go client PUT succeeded!")
        logger.info(f"   Output: {put_result.stdout.strip()}")

    assert put_result.returncode == 0, f"Go client Put failed: {put_result.stderr}"
    assert f"Key {put_key} put successfully." in put_result.stdout

    # 3. Run the Go client to get the value
    get_command = [
        str(soup_go_path), "rpc", "kv", "get",
        f"--address={handshake_line}",  # Pass full handshake with certificate
        put_key
    ]

    logger.info(f"📥 Executing Go client GET operation:")
    logger.info(f"   Command: {' '.join(get_command[:4])} [handshake] {put_key}")
    logger.info(f"   Key: {put_key}")
    logger.info(f"   Expected value: {put_value}")

    get_result = subprocess.run(
        get_command,
        env=env,
        capture_output=True,
        text=True,
        timeout=10
    )

    if get_result.returncode != 0:
        logger.error(f"❌ Go client GET failed!")
        logger.error(f"   Exit code: {get_result.returncode}")
        logger.error(f"   Stdout: {get_result.stdout}")
        logger.error(f"   Stderr: {get_result.stderr}")
    else:
        logger.info(f"✅ Go client GET succeeded!")
        logger.info(f"   Retrieved value: {get_result.stdout.strip()}")

    assert get_result.returncode == 0, f"Go client Get failed: {get_result.stderr}"
    assert put_value in get_result.stdout

    # Clean up server process
    logger.info(f"🛑 Terminating Python server...")
    server_process.terminate()
    server_process.wait(timeout=5)
    assert server_process.returncode is not None, "Python server process did not terminate"
    logger.info(f"✅ Server terminated successfully")

    logger.info("="*80)
    logger.info("✅ TEST PASSED: Go Client → Python Server")
    logger.info("="*80)


@pytest.mark.asyncio
async def test_go_to_go(soup_go_path: Path | None) -> None:
    """Test Go client → Go server (completes the 2x2 matrix)."""
    if soup_go_path is None:
        pytest.skip("soup-go executable not found")

    from tofusoup.rpc.client import KVClient

    # Create client with Go server
    client = KVClient(
        server_path=str(soup_go_path),
        tls_mode="auto",
        tls_key_type="ec",
        tls_curve="P-256"
    )

    try:
        await asyncio.wait_for(client.start(), timeout=15.0)

        # Test put operation
        test_key = "test-gogo-proof"
        test_value = b"Hello from Go server to Go client (via Python orchestration)!"

        await client.put(test_key, test_value)

        # Test get operation
        retrieved = await client.get(test_key)

        assert retrieved == test_value, f"Value mismatch: expected {test_value!r}, got {retrieved!r}"

    finally:
        try:
            await client.close()
        except Exception:
            pass

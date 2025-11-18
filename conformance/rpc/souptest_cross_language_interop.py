#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Cross-Language Interoperability Test for TofuSoup

This test proves that the Go RPC server and Python RPC server can be used
interchangeably with both Go and Python clients, demonstrating true
cross-language compatibility using the centralized proto definitions.

Test Matrix:
1. Python Client ↔ Go Server
2. Python Client ↔ Python Server
3. Go Client ↔ Python Server (via subprocess)
4. Go Client ↔ Go Server (via subprocess)"""

import asyncio
import os
from pathlib import Path
import subprocess
import time

import grpc.aio
from provide.foundation import logger
import pytest

from tofusoup.rpc.client import KVClient
from tofusoup.rpc.server import serve


@pytest.fixture
def soup_path() -> Path | None:
    """Find the soup executable (Python)."""
    import shutil

    soup = shutil.which("soup")
    if soup:
        return Path(soup)
    return None


class TestCrossLanguageInterop:
    """Test cross-language RPC interoperability."""

    @pytest.fixture
    async def python_server_address(self, tmp_path: Path) -> str:
        """Start a Python KV server with isolated storage and return its address."""
        server = grpc.aio.server()
        port = server.add_insecure_port("[::]:0")  # Get available port
        # Use isolated temp directory for this server instance
        serve(server, storage_dir=str(tmp_path))
        await server.start()
        address = f"127.0.0.1:{port}"
        logger.info(f"Started Python KV server at {address}", storage_dir=str(tmp_path))
        yield address
        await server.stop(0)
        logger.info(f"Stopped Python KV server at {address}")

    @pytest.fixture
    def go_server_path(self) -> str | None:
        """Return path to Go server binary if it exists."""
        # Use the new unified soup-go harness
        go_server_candidates = [
            "bin/soup-go",
            "harnesses/bin/soup-go",
            Path(__file__).parent.parent.parent / "bin" / "soup-go",
        ]

        for candidate in go_server_candidates:
            candidate_path = Path(candidate) if isinstance(candidate, str) else candidate
            if candidate_path.exists() and os.access(candidate_path, os.X_OK):
                logger.info(f"Found Go server at {candidate_path}")
                return str(candidate_path)

        logger.warning("soup-go binary not found, skipping Go server tests")
        return None

    @pytest.fixture
    def go_client_path(self) -> str | None:
        """Return path to Go client binary if it exists."""
        # Use the new unified soup-go harness for client testing too
        go_client_candidates = [
            "bin/soup-go",
            "harnesses/bin/soup-go",
            Path(__file__).parent.parent.parent / "bin" / "soup-go",
        ]

        for candidate in go_client_candidates:
            candidate_path = Path(candidate) if isinstance(candidate, str) else candidate
            if candidate_path.exists() and os.access(candidate_path, os.X_OK):
                logger.info(f"Found Go client at {candidate_path}")
                return str(candidate_path)

        logger.warning("soup-go binary not found, skipping Go client tests")
        return None

    @pytest.mark.integration_rpc
    @pytest.mark.harness_python
    async def test_python_client_python_server(self, python_server_address: str) -> None:
        """Test: Python Client ↔ Python Server"""

        # Create a simple direct gRPC client for testing
        from tofusoup.harness.proto.kv import kv_pb2, kv_pb2_grpc

        channel = grpc.aio.insecure_channel(python_server_address)
        stub = kv_pb2_grpc.KVStub(channel)

        test_key = "python-to-python"
        test_value = b"Hello from Python client to Python server!"

        # Test Put
        await stub.Put(kv_pb2.PutRequest(key=test_key, value=test_value))

        # Test Get
        response = await stub.Get(kv_pb2.GetRequest(key=test_key))
        assert response.value == test_value

        await channel.close()

    @pytest.mark.integration_rpc
    @pytest.mark.harness_go
    @pytest.mark.skipif(os.getenv("SKIP_GO_TESTS"), reason="Go tests skipped")
    async def test_python_client_go_server(self, go_server_path: str) -> None:
        """Test: Python Client ↔ Go Server"""
        if not go_server_path:
            pytest.skip("Go server binary not available")

        # Use our KVClient to connect to Go server with auto TLS
        client = KVClient(server_path=go_server_path, tls_mode="auto", tls_key_type="ec", tls_curve="P-256")

        try:
            await client.start()

            test_key = "python-to-go"
            test_value = b"Hello from Python client to Go server!"

            # Test Put
            await client.put(test_key, test_value)

            # Test Get
            retrieved_value = await client.get(test_key)
            assert retrieved_value == test_value

            # Test Get non-existent key
            non_existent = await client.get("non-existent-key")
            assert non_existent is None

        finally:
            await client.close()

    @pytest.mark.integration_rpc
    @pytest.mark.harness_go
    @pytest.mark.harness_python
    @pytest.mark.skipif(os.getenv("SKIP_GO_TESTS"), reason="Go tests skipped")
    async def test_go_client_python_server(
        self, go_client_path: str, soup_path: Path | None, test_artifacts_dir: Path
    ) -> None:
        """Test: Go Client ↔ Python Server by explicitly starting server and client."""
        if not go_client_path:
            pytest.skip("Go client binary not available")
        if soup_path is None:
            pytest.skip("soup executable not found in PATH")

        # Create test-specific directory for all artifacts
        test_dir = test_artifacts_dir / "go_client_python_server"
        test_dir.mkdir(exist_ok=True)

        env = os.environ.copy()
        env["KV_STORAGE_DIR"] = str(test_dir)
        env["LOG_LEVEL"] = "INFO"
        env["BASIC_PLUGIN"] = "hello"
        env["PLUGIN_MAGIC_COOKIE_KEY"] = "BASIC_PLUGIN"

        # 1. Start the Python server
        server_command = [
            str(soup_path),
            "rpc",
            "kv",
            "server",
            "--tls-mode",
            "auto",
            "--tls-curve",
            "secp256r1",
        ]
        server_process = subprocess.Popen(
            server_command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Wait for the server to start and output its handshake
        handshake_line = ""
        timeout_seconds = 30
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            line = server_process.stdout.readline()
            if line:
                # Look for the go-plugin handshake pattern: starts with "1|1|tcp|" or "1|1|unix|"
                if (
                    line.startswith("1|1|tcp|")
                    or line.startswith("1|1|unix|")
                    or "|tcp|" in line
                    or "|unix|" in line
                ):
                    handshake_line = line.strip()
                    break
            else:
                # If no line, give the server a moment to produce output
                await asyncio.sleep(0.1)

            # Check if the process has terminated prematurely
            if server_process.poll() is not None:
                stderr_output = server_process.stderr.read()
                raise AssertionError(f"Server process terminated prematurely. Stderr: {stderr_output}")
        assert handshake_line, "Python server did not output handshake line"

        # Extract port from handshake line
        parts = handshake_line.split("|")
        assert len(parts) == 6, f"Invalid handshake line format: {handshake_line}"
        address_part = parts[3]
        address_part.split(":")[-1]

        # 2. Run the Go client to put a value
        # IMPORTANT: Pass the FULL handshake line (including certificate) so Go client can auto-detect TLS curve
        put_key = "go-py-key-interop"
        put_value = "Hello from Go client to Python server (interop)!"
        put_command = [
            go_client_path,
            "rpc",
            "kv",
            "put",
            f"--address={handshake_line}",  # Pass full handshake with certificate for TLS curve auto-detection
            put_key,
            put_value,
        ]
        put_result = subprocess.run(put_command, env=env, capture_output=True, text=True, timeout=10)
        assert put_result.returncode == 0, f"Go client Put failed: {put_result.stderr}"
        assert f"Key {put_key} put successfully." in put_result.stdout

        # 3. Run the Go client to get the value
        get_command = [
            go_client_path,
            "rpc",
            "kv",
            "get",
            f"--address={handshake_line}",  # Pass full handshake with certificate
            put_key,
        ]
        get_result = subprocess.run(get_command, env=env, capture_output=True, text=True, timeout=10)
        assert get_result.returncode == 0, f"Go client Get failed: {get_result.stderr}"
        assert put_value in get_result.stdout

        # Clean up server process
        server_process.terminate()
        server_process.wait(timeout=5)
        assert server_process.returncode is not None, "Python server process did not terminate"

    @pytest.mark.integration_rpc
    def test_proto_compatibility(self) -> None:
        """Test: Verify proto message compatibility"""
        logger.info("🔄 Testing Proto Message Compatibility")

        from tofusoup.harness.proto.kv import kv_pb2

        # Test that we can create and serialize/deserialize messages
        put_request = kv_pb2.PutRequest(key="test-key", value=b"test-value")
        serialized = put_request.SerializeToString()

        # Deserialize it back
        put_request2 = kv_pb2.PutRequest()
        put_request2.ParseFromString(serialized)

        assert put_request2.key == "test-key"
        assert put_request2.value == b"test-value"

        # Test Empty message
        empty = kv_pb2.Empty()
        empty_serialized = empty.SerializeToString()
        empty2 = kv_pb2.Empty()
        empty2.ParseFromString(empty_serialized)

    @pytest.mark.integration_rpc
    @pytest.mark.harness_python
    @pytest.mark.harness_go
    async def test_comprehensive_interop_scenario(
        self, python_server_address: str, go_server_path: str | None
    ) -> None:
        """Test: Comprehensive interoperability scenario"""
        logger.info("🌐 Testing Comprehensive Interoperability Scenario")

        # Test data
        test_data = {
            "python-server-key": b"Data stored via Python server",
            "go-server-key": b"Data stored via Go server",
            "binary-data": bytes(range(256)),  # Full byte range
            "empty-value": b"",
            "large-value": b"x" * 10000,  # 10KB value
        }

        # Test Python server with direct gRPC
        from tofusoup.harness.proto.kv import kv_pb2, kv_pb2_grpc

        channel = grpc.aio.insecure_channel(python_server_address)
        py_stub = kv_pb2_grpc.KVStub(channel)

        # Store all test data in Python server
        for key, value in test_data.items():
            await py_stub.Put(kv_pb2.PutRequest(key=f"py-{key}", value=value))

        # Retrieve and verify from Python server
        for key, expected_value in test_data.items():
            response = await py_stub.Get(kv_pb2.GetRequest(key=f"py-{key}"))
            assert response.value == expected_value, f"Python server failed for key: {key}"

        await channel.close()

        # Test Go server if available
        if go_server_path:
            client = KVClient(server_path=go_server_path, tls_mode="disabled")
            try:
                await client.start()

                # Store all test data in Go server
                for key, value in test_data.items():
                    await client.put(f"go-{key}", value)

                # Retrieve and verify from Go server
                for key, expected_value in test_data.items():
                    retrieved = await client.get(f"go-{key}")
                    assert retrieved == expected_value, f"Go server failed for key: {key}"

            finally:
                await client.close()
        else:
            logger.info("⏭️  Skipping Go server comprehensive test (binary not available)")


if __name__ == "__main__":
    # Run a quick manual test
    async def manual_test() -> None:
        test_instance = TestCrossLanguageInterop()
        test_instance.test_proto_compatibility()

    asyncio.run(manual_test())

# 🥣🔬🔚

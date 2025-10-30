#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Harness Factory for RPC K/V Matrix Testing

Creates Go and Python RPC clients and servers dynamically based on
matrix parameters. Handles certificate configuration and process management."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import os
from pathlib import Path
import subprocess
from typing import Any, Never

from provide.foundation import logger

from tofusoup.common.config import load_tofusoup_config
from tofusoup.harness.logic import ensure_go_harness_build
from tofusoup.rpc.client import KVClient

from .cert_manager import CertificateManager
from .matrix_config import CryptoConfig


class ReferenceKVServer:
    """Base class for KV server implementations."""

    def __init__(
        self,
        crypto_config: CryptoConfig,
        work_dir: Path,
        combo_id: str | None = None,
        server_language: str | None = None,
    ) -> None:
        self.crypto_config = crypto_config
        self.work_dir = work_dir
        self.combo_id = combo_id or "default"
        self.server_language = server_language or "unknown"
        self.address: str | None = None
        # Create combo-specific storage directory
        self.storage_dir = work_dir / f"kv-{self.combo_id}"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


class GoKVServer(ReferenceKVServer):
    """Go KV server implementation using subprocess."""

    def __init__(
        self,
        crypto_config: CryptoConfig,
        work_dir: Path,
        combo_id: str | None = None,
        client_language: str | None = None,
    ) -> None:
        super().__init__(crypto_config, work_dir, combo_id, server_language="go")
        self.process: subprocess.Popen | None = None
        self.server_port: int | None = None
        self.client_language = client_language or "unknown"

    async def start(self) -> None:
        """Start Go KV server process."""

        # Build soup-go harness if needed
        project_root = Path(__file__).parent.parent.parent
        config = load_tofusoup_config(project_root)
        soup_go_path = ensure_go_harness_build("soup-go", project_root, config)

        # Prepare soup-go command arguments
        args = [str(soup_go_path), "rpc", "kv", "server"]
        args.extend(self.crypto_config.to_go_cli_args())
        print(f"DEBUG: soup-go args: {args}")

        # For auto_mtls mode, the Go server generates certificates automatically
        # No additional certificate flags needed

        # Set up environment with combo identification
        env = os.environ.copy()
        env.update(
            {
                "LOG_LEVEL": "TRACE",
                "PYTHONUNBUFFERED": "1",
                "KV_STORAGE_DIR": str(self.storage_dir),
                "SERVER_LANGUAGE": self.server_language,
                "CLIENT_LANGUAGE": self.client_language,
                "COMBO_ID": self.combo_id,
                "TLS_MODE": self.crypto_config.auth_mode,
                "TLS_KEY_TYPE": self.crypto_config.key_type,
                "TLS_KEY_SIZE": str(self.crypto_config.key_size),
            }
        )

        # Start Go server process
        logger.info(f"Starting Go KV server via soup-go: {' '.join(args)}")
        print(f"DEBUG: Full command: {' '.join(args)}")
        self.process = subprocess.Popen(
            args, env=env, cwd=self.work_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Wait for server to start and parse address from stdout
        # The soup-go server-start command prints the address to stdout
        server_started = False
        while not server_started:
            line = self.process.stdout.readline()
            if "Server listening on" in line:
                self.address = line.split("Server listening on ")[1].strip()
                self.server_port = int(self.address.split(":")[-1])
                server_started = True
            elif self.process.poll() is not None:
                # Process exited before printing address, something went wrong
                stdout, stderr = self.process.communicate()
                raise RuntimeError(f"Go server failed to start. Stdout: {stdout}, Stderr: {stderr}")
            await asyncio.sleep(0.1)  # Avoid busy-waiting

        logger.info(f"Go KV server started at {self.address}")

    async def stop(self) -> None:
        """Stop Go KV server process."""
        if self.process:
            logger.info("Stopping Go KV server")
            self.process.terminate()
            try:
                await asyncio.wait_for(asyncio.create_task(self._wait_for_process()), timeout=5.0)
            except TimeoutError:
                logger.warning("Go KV server did not terminate gracefully, killing")
                self.process.kill()
                await self._wait_for_process()

    async def _wait_for_process(self) -> None:
        """Wait for process to terminate in async context."""
        while self.process and self.process.poll() is None:
            await asyncio.sleep(0.1)


class PythonKVServer(ReferenceKVServer):
    """Python KV server implementation - use existing TofuSoup KV server."""

    def __init__(
        self,
        crypto_config: CryptoConfig,
        work_dir: Path,
        combo_id: str | None = None,
        client_language: str | None = None,
    ) -> None:
        super().__init__(crypto_config, work_dir, combo_id, server_language="python")
        self.process: subprocess.Popen | None = None
        self.client_language = client_language or "unknown"

    async def start(self) -> None:
        """Start Python KV server using TofuSoup's server."""

        # Generate certificates if needed
        cert_manager = CertificateManager(self.work_dir)
        cert_files = cert_manager.generate_crypto_material(self.crypto_config)

        # Use the existing TofuSoup KV server
        import tofusoup.rpc.server as kv_server_module

        server_script = Path(kv_server_module.__file__)

        # Build command to run Python KV server
        cmd = ["python", str(server_script)]

        # Set up environment with combo identification
        env = os.environ.copy()
        env.update(
            {
                "KV_STORAGE_DIR": str(self.storage_dir),
                "SERVER_LANGUAGE": self.server_language,
                "CLIENT_LANGUAGE": self.client_language,
                "COMBO_ID": self.combo_id,
                "TLS_MODE": self.crypto_config.auth_mode,
                "TLS_KEY_TYPE": self.crypto_config.key_type,
                "TLS_KEY_SIZE": str(self.crypto_config.key_size),
            }
        )
        if self.crypto_config.auth_mode == "auto_mtls":
            env.update(
                {
                    "KV_SERVER_CERT": str(cert_files["server_cert"]),
                    "KV_SERVER_KEY": str(cert_files["server_key"]),
                    "KV_CA_CERT": str(cert_files["ca_cert"]),
                    "ENABLE_MTLS": "true",
                }
            )

        logger.info(f"Starting Python KV server: {' '.join(cmd)}")
        self.process = subprocess.Popen(
            cmd, env=env, cwd=self.work_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Wait for server to start
        await asyncio.sleep(2)  # Give server time to start
        self.address = "127.0.0.1:50051"  # Default port from server.py

        logger.info(f"Python KV server started at {self.address}")

    async def stop(self) -> None:
        """Stop Python KV server."""
        if self.process:
            logger.info("Stopping Python KV server")
            self.process.terminate()
            try:
                await asyncio.wait_for(asyncio.create_task(self._wait_for_process()), timeout=5.0)
            except TimeoutError:
                logger.warning("Python KV server did not terminate gracefully, killing")
                self.process.kill()
                await self._wait_for_process()

    async def _wait_for_process(self) -> None:
        """Wait for process to terminate in async context."""
        while self.process and self.process.poll() is None:
            await asyncio.sleep(0.1)


class ReferenceKVClient:
    """Base class for KV client implementations."""

    def __init__(self, crypto_config: CryptoConfig, server_address: str, work_dir: Path) -> None:
        self.crypto_config = crypto_config
        self.server_address = server_address
        self.work_dir = work_dir

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def put(self, key: str, value: bytes) -> Never:
        """Put key-value pair."""
        raise NotImplementedError

    async def get(self, key: str) -> bytes | None:
        """Get value by key."""
        raise NotImplementedError

    async def delete(self, key: str) -> Never:
        """Delete key."""
        raise NotImplementedError


class GoKVClient(ReferenceKVClient):
    """Go KV client implementation using subprocess."""

    def __init__(self, crypto_config: CryptoConfig, server_address: str, work_dir: Path) -> None:
        super().__init__(crypto_config, server_address, work_dir)
        self.go_client_path: str | None = None

    async def start(self) -> None:
        """Initialize Go KV client."""
        # Build Go client harness if needed
        project_root = Path(__file__).parent.parent.parent
        config = load_tofusoup_config(project_root)
        self.go_client_path = ensure_go_harness_build("go-rpc-client", project_root, config)
        logger.info(f"Go KV client initialized with binary: {self.go_client_path}")

    async def stop(self) -> None:
        """Cleanup Go KV client."""
        pass  # No persistent process to stop

    async def _run_go_command(self, operation: str, key: str, value: bytes | None = None) -> bytes:
        """Run Go client command and return output."""

        cert_manager = CertificateManager(self.work_dir)
        cert_files = cert_manager.generate_crypto_material(self.crypto_config)

        args = [self.go_client_path, operation, key]
        if value is not None:
            args.append(value.decode("utf-8"))

        # Add crypto configuration
        args.extend(self.crypto_config.to_go_cli_args())
        args.extend(
            [
                f"--server-address={self.server_address}",
                f"--ca-cert={cert_files['ca_cert']}",
                f"--client-cert={cert_files['client_cert']}",
                f"--client-key={cert_files['client_key']}",
            ]
        )

        env = os.environ.copy()
        env.update({"PLUGIN_MAGIC_COOKIE_KEY": "BASIC_PLUGIN", "BASIC_PLUGIN": "hello"})

        logger.debug(f"Running Go client command: {' '.join(args)}")
        process = subprocess.run(args, env=env, cwd=self.work_dir, capture_output=True, text=True)

        if process.returncode != 0:
            raise RuntimeError(f"Go client command failed: {process.stderr}")

        return process.stdout.encode("utf-8")

    async def put(self, key: str, value: bytes) -> None:
        """Put key-value pair using Go client."""
        await self._run_go_command("put", key, value)

    async def get(self, key: str) -> bytes | None:
        """Get value by key using Go client."""
        try:
            result = await self._run_go_command("get", key)
            return result.strip() if result else None
        except RuntimeError:
            return None  # Key not found

    async def delete(self, key: str) -> None:
        """Delete key using Go client."""
        await self._run_go_command("delete", key)


class PythonKVClient(ReferenceKVClient):
    """Python KV client implementation using TofuSoup's KVClient."""

    def __init__(self, crypto_config: CryptoConfig, server_address: str, work_dir: Path) -> None:
        super().__init__(crypto_config, server_address, work_dir)
        self.client: KVClient | None = None

    async def start(self) -> None:
        """Initialize Python KV client using TofuSoup's KVClient."""

        # Create a simple server executable that returns the server address
        # This is how TofuSoup's KVClient expects to get server connection info
        server_script = self.work_dir / "server_info.py"
        with server_script.open("w") as f:
            f.write(f'''#!/usr/bin/env python3
import sys
print("{self.server_address}")
sys.exit(0)
''')
        server_script.chmod(0o755)

        # Configure crypto settings for KVClient

        if self.crypto_config.key_type == "rsa":
            pass
        elif self.crypto_config.key_type == "ec":
            # Map EC sizes to curve names that KVClient expects
            curve_map = {256: "P-256", 384: "P-384", 521: "P-521"}
            curve_map.get(self.crypto_config.key_size, "P-384")

        # Determine tls_mode based on crypto_config
        tls_mode = "auto" if self.crypto_config.auth_mode == "auto_mtls" else "disabled"
        tls_key_type = None

        if self.crypto_config.key_type == "rsa":
            tls_key_type = "rsa"
        elif self.crypto_config.key_type == "ec":
            tls_key_type = "ec"  # KVClient expects "ec" for ECDSA, not curve name

        # Create KVClient with appropriate crypto settings
        self.client = KVClient(
            server_path=str(server_script),
            tls_mode=tls_mode,
            tls_key_type=tls_key_type,
            # cert_file and key_file are not needed for auto_mtls as they are handled by env vars
        )

        await self.client.start()
        logger.info("Python KV client started")

    async def stop(self) -> None:
        """Stop Python KV client."""
        if self.client:
            await self.client.close()
            logger.info("Python KV client stopped")

    async def put(self, key: str, value: bytes) -> None:
        """Put key-value pair using Python client."""
        await self.client.put(key, value)

    async def get(self, key: str) -> bytes | None:
        """Get value by key using Python client."""
        return await self.client.get(key)

    async def delete(self, key: str) -> None:
        """Delete key using Python client."""
        # TofuSoup KVClient might not have delete implemented
        pass


# Factory functions


@asynccontextmanager
async def create_kv_server(
    language: str,
    crypto_config: CryptoConfig,
    work_dir: Path,
    combo_id: str | None = None,
    client_language: str | None = None,
) -> AsyncGenerator[ReferenceKVServer, None]:
    """Factory function for creating KV servers."""

    if language == "go":
        server = GoKVServer(crypto_config, work_dir, combo_id, client_language)
    elif language == "pyvider":
        server = PythonKVServer(crypto_config, work_dir, combo_id, client_language)
    else:
        raise ValueError(f"Unsupported server language: {language}")

    async with server:
        yield server


@asynccontextmanager
async def create_kv_client(
    language: str, crypto_config: CryptoConfig, server_address: str, work_dir: Path
) -> AsyncGenerator[ReferenceKVClient, None]:
    """Factory function for creating KV clients."""

    if language == "go":
        client = GoKVClient(crypto_config, server_address, work_dir)
    elif language == "pyvider":
        client = PythonKVClient(crypto_config, server_address, work_dir)
    else:
        raise ValueError(f"Unsupported client language: {language}")

    async with client:
        yield client


def get_factory_info() -> dict[str, Any]:
    """Get information about supported factory configurations."""
    return {
        "supported_languages": ["go", "pyvider"],
        "supported_auth_modes": ["auto_mtls"],
        "supported_key_types": ["rsa", "ec"],
        "supported_rsa_sizes": [2048, 4096],
        "supported_ec_curves": [256, 384, 521],
    }


# 🥣🔬🔚

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

    async def __aenter__(self) -> "ReferenceKVServer":
        await self.start()
        return self

    async def __aexit__(
        self, exc_type: BaseException | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
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
        # Let server auto-generate its certs - simpler than managing cert files
        args = [str(soup_go_path), "rpc", "kv", "server"]
        args.extend(self.crypto_config.to_go_cli_args())

        print(f"DEBUG: soup-go args: {args}")

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
        """Start Python KV server using TofuSoup's soup CLI."""

        # Generate certificates if needed
        cert_manager = CertificateManager(self.work_dir)
        cert_manager.generate_crypto_material(self.crypto_config)

        # Find soup binary
        import shutil

        soup_path = shutil.which("soup")
        if not soup_path:
            raise RuntimeError("soup command not found in PATH. Please ensure TofuSoup is properly installed.")

        # Build soup rpc kv server command
        # Use TCP transport to work around Unix socket issues in pyvider-rpcplugin
        args = [soup_path, "rpc", "kv", "server", "--transport", "tcp"]
        args.extend(self.crypto_config.to_python_cli_args())

        logger.debug(f"Python server args: {args}")

        # Set up environment with combo identification
        # CRITICAL: Do NOT set LOG_LEVEL=TRACE/DEBUG, as it will print to stdout
        # and corrupt the go-plugin handshake which must be the only stdout output.
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

        logger.info(f"Starting Python KV server via soup: {' '.join(args)}")
        self.process = subprocess.Popen(
            args, env=env, cwd=self.work_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # The Python server uses go-plugin protocol handled by pyvider-rpcplugin.
        # The RPCPluginClient (used by KVClient) will parse the handshake from stdout.
        # We just need to store a placeholder address - the actual connection is handled
        # by the client code which uses the server_path (soup binary) directly.
        self.address = "unix-socket"  # Placeholder - actual socket is handled by pyvider
        self.server_port = None  # Python servers use Unix sockets, not TCP ports

        logger.info(f"Python KV server process started (PID: {self.process.pid})")

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

    async def __aenter__(self) -> "ReferenceKVClient":
        await self.start()
        return self

    async def __aexit__(
        self, exc_type: BaseException | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
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
        # Build soup-go harness (which includes client functionality)
        project_root = Path(__file__).parent.parent.parent
        config = load_tofusoup_config(project_root)
        self.go_client_path = str(ensure_go_harness_build("soup-go", project_root, config))
        logger.info(f"Go KV client initialized with binary: {self.go_client_path}")

    async def stop(self) -> None:
        """Cleanup Go KV client."""
        # No persistent process to stop

    async def _run_go_command(self, operation: str, key: str, value: bytes | None = None) -> bytes:
        """Run Go client command and return output."""

        # Use 127.0.0.1 instead of the server's bind address (which might be [::])
        port = self.server_address.split(":")[-1]
        client_address = f"127.0.0.1:{port}"

        # soup-go command structure: soup-go rpc kv <operation> <key> [value]
        args = [self.go_client_path, "rpc", "kv", operation, key]
        if value is not None:
            args.append(value.decode("utf-8"))

        # Pass the address
        args.extend(["--address", client_address])

        # Add TLS curve configuration
        if self.crypto_config.key_type == "ec":
            # Map key sizes to curve names
            curve_map = {256: "secp256r1", 384: "secp384r1", 521: "secp521r1"}
            curve = curve_map.get(self.crypto_config.key_size, "auto")
            args.extend(["--tls-curve", curve])
        else:
            # For RSA, use auto curve detection
            args.extend(["--tls-curve", "auto"])

        env = os.environ.copy()
        # Enable AutoMTLS mode
        env.update(
            {
                "PLUGIN_AUTO_MTLS": "1",  # Enable AutoMTLS
            }
        )

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

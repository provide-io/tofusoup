# type: ignore
#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""KV Plugin Server using pyvider-rpcplugin.

This module provides a simple Key-Value store plugin server that uses
pyvider-rpcplugin for proper go-plugin protocol support. It handles:
- go-plugin handshake protocol (via pyvider-rpcplugin)
- Auto-mTLS certificate generation (via pyvider-rpcplugin)
- gRPC service hosting (via pyvider-rpcplugin)

Usage:
    As a plugin (spawned by client):
        PLUGIN_MAGIC_COOKIE_KEY=BASIC_PLUGIN BASIC_PLUGIN=hello \\
        TLS_MODE=auto TLS_KEY_TYPE=ec TLS_CURVE=secp256r1 \\
        python server.py

    Standalone mode (for testing):
        python server.py --standalone --port 50051
"""

import asyncio
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any

import grpc
from provide.foundation import logger

from pyvider.rpcplugin.protocol.base import RPCPluginProtocol
from pyvider.rpcplugin.server import RPCPluginServer
from tofusoup.common.utils import get_cache_dir
from tofusoup.config.defaults import DEFAULT_GRPC_PORT, ENV_KV_STORAGE_DIR
from tofusoup.harness.proto.kv import kv_pb2, kv_pb2_grpc


class KV(kv_pb2_grpc.KVServicer):
    """Key-Value store implementation."""

    def __init__(self, storage_dir: str | None = None) -> None:
        """Initialize KV servicer with configurable storage directory.

        Args:
            storage_dir: Directory to store KV data files. Defaults to XDG_CACHE_HOME/tofusoup/kv-store.
        """
        if storage_dir is None:
            storage_dir = str(get_cache_dir() / "kv-store")
        self.storage_dir = storage_dir
        self.key_pattern = re.compile(r"^[a-zA-Z0-9._-]+$")
        self.start_time = time.time()
        logger.debug("Initialized KV servicer", storage_dir=storage_dir)

    def _validate_key(self, key: str) -> bool:
        """Validate that key contains only allowed characters [a-zA-Z0-9._-]"""
        return bool(self.key_pattern.match(key))

    def _get_file_path(self, key: str) -> str:
        """Get the file path for a given key"""
        return f"{self.storage_dir}/kv-data-{key}"

    def _enrich_json_with_handshake(self, value_bytes: bytes, context: grpc.ServicerContext) -> bytes:
        """Enrich JSON value with server handshake information.

        If the value is valid JSON, adds a 'server_handshake' field with connection metadata.
        If not JSON, returns the original bytes unchanged.

        Args:
            value_bytes: The value bytes to potentially enrich
            context: gRPC service context

        Returns:
            Enriched JSON bytes if input was JSON, otherwise original bytes
        """
        try:
            # Try to parse as JSON
            value_str = value_bytes.decode("utf-8")
            json_data = json.loads(value_str)

            # Only enrich if it's a dict (not array or primitive)
            if not isinstance(json_data, dict):
                return value_bytes

            # Build server handshake information with combo identification
            peer = context.peer()  # e.g., "ipv4:127.0.0.1:54321"

            server_handshake = {
                "endpoint": peer if peer else "unknown",
                "protocol_version": os.getenv("PLUGIN_PROTOCOL_VERSIONS", "1"),
                "tls_mode": os.getenv("TLS_MODE", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "received_at": round(time.time() - self.start_time, 3),
                # Combo identification
                "server_language": os.getenv("SERVER_LANGUAGE", "python"),
                "client_language": os.getenv("CLIENT_LANGUAGE", "unknown"),
                "combo_id": os.getenv("COMBO_ID", "unknown"),
            }

            # Add enhanced crypto configuration
            tls_key_type = os.getenv("TLS_KEY_TYPE")
            tls_key_size = os.getenv("TLS_KEY_SIZE")
            tls_curve = os.getenv("TLS_CURVE")

            if tls_key_type:
                crypto_config: dict[str, Any] = {"key_type": tls_key_type}

                if tls_key_type == "rsa" and tls_key_size:
                    crypto_config["key_size"] = int(tls_key_size)
                elif tls_key_type == "ec" and tls_curve:
                    crypto_config["curve"] = tls_curve
                    # Map curve to key size for reference
                    curve_sizes = {"secp256r1": 256, "secp384r1": 384, "secp521r1": 521}
                    if tls_curve in curve_sizes:
                        crypto_config["key_size"] = curve_sizes[tls_curve]

                server_handshake["crypto_config"] = crypto_config

            # Add certificate fingerprint if mTLS is enabled
            server_cert = os.getenv("PLUGIN_SERVER_CERT")
            if server_cert:
                try:
                    with Path(server_cert).open("rb") as f:
                        cert_bytes = f.read()
                        cert_fingerprint = hashlib.sha256(cert_bytes).hexdigest()
                        server_handshake["cert_fingerprint"] = cert_fingerprint
                except Exception:
                    server_handshake["cert_fingerprint"] = None

            # Add server handshake to JSON
            json_data["server_handshake"] = server_handshake

            # Return enriched JSON as bytes
            enriched_json = json.dumps(json_data, indent=2)
            logger.debug("Enriched JSON value with server handshake", key_count=len(json_data))
            return enriched_json.encode("utf-8")

        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            # Not JSON or not decodable - return original bytes
            logger.debug("Value is not JSON, storing as-is")
            return value_bytes
        except Exception as e:
            # Unexpected error - log and return original
            logger.warning("Failed to enrich JSON with handshake", error=str(e))
            return value_bytes

    def Get(self, request: kv_pb2.GetRequest, context: grpc.ServicerContext) -> kv_pb2.GetResponse:
        if not self._validate_key(request.key):
            logger.error("Invalid key for Get operation", key=request.key)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(
                f'Key "{request.key}" contains invalid characters, only [a-zA-Z0-9._-] are allowed'
            )
            return kv_pb2.GetResponse()

        file_path = self._get_file_path(request.key)
        logger.debug("Retrieving value from file", key=request.key, file=file_path)

        try:
            with Path(file_path).open("rb") as f:
                raw_value = f.read()

            # Enrich JSON values with server handshake information on Get
            enriched_value = self._enrich_json_with_handshake(raw_value, context)

            logger.info(
                "Successfully retrieved value",
                key=request.key,
                file=file_path,
                raw_bytes=len(raw_value),
                enriched_bytes=len(enriched_value),
            )
            return kv_pb2.GetResponse(value=enriched_value)
        except FileNotFoundError:
            logger.warning("Key not found during Get operation", key=request.key, file=file_path)
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Key not found: {request.key}")
            return kv_pb2.GetResponse()
        except Exception as e:
            logger.error(
                "Failed to read value from file",
                key=request.key,
                file=file_path,
                error=str(e),
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Failed to read key "{request.key}" from file: {e}')
            return kv_pb2.GetResponse()

    def Put(self, request: kv_pb2.PutRequest, context: grpc.ServicerContext) -> kv_pb2.Empty:
        if not self._validate_key(request.key):
            logger.error("Invalid key for Put operation", key=request.key)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(
                f'Key "{request.key}" contains invalid characters, only [a-zA-Z0-9._-] are allowed'
            )
            return kv_pb2.Empty()

        file_path = self._get_file_path(request.key)
        logger.debug("Storing value to file", key=request.key, file=file_path)

        try:
            # Store raw value without enrichment (enrichment happens on Get)
            with Path(file_path).open("wb") as f:
                f.write(request.value)
            logger.info(
                "Successfully stored value",
                key=request.key,
                file=file_path,
                bytes=len(request.value),
            )
            return kv_pb2.Empty()
        except Exception as e:
            logger.error(
                "Failed to write value to file",
                key=request.key,
                file=file_path,
                error=str(e),
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Failed to write key "{request.key}" to file: {e}')
            return kv_pb2.Empty()


def serve(server: grpc.aio.Server, storage_dir: str | None = None) -> None:
    """Set up KV handlers on a gRPC server.

    This is a helper function for testing that adds the KV servicer
    to an existing gRPC server without using the plugin protocol.

    Args:
        server: The gRPC async server to add handlers to.
        storage_dir: Directory to store KV data files.
    """
    handler = KV(storage_dir=storage_dir)
    kv_pb2_grpc.add_KVServicer_to_server(handler, server)
    logger.info("Added KV servicer to gRPC server", storage_dir=storage_dir)


class KVProtocol(RPCPluginProtocol[grpc.aio.Server, KV]):
    """Protocol implementation for KV service."""

    service_name = "tofusoup.kv.KVService"

    def __init__(self, storage_dir: str | None = None) -> None:
        """Initialize protocol with storage directory."""
        self.storage_dir = storage_dir

    async def get_grpc_descriptors(self) -> tuple[None, str]:
        """Return service descriptors (not needed for simple case)."""
        return None, self.service_name

    async def add_to_server(self, server: grpc.aio.Server, handler: KV) -> None:
        """Add the KV service to the gRPC server."""
        kv_pb2_grpc.add_KVServicer_to_server(handler, server)
        logger.info("Added KV servicer to gRPC server")


async def serve_plugin(
    storage_dir: str | None = None,
    tls_mode: str | None = None,
    tls_key_type: str | None = None,
    tls_curve: str | None = None,
    transport: str | None = None,
) -> None:
    """Start the KV plugin server using pyvider-rpcplugin.

    This handles the complete plugin protocol including:
    - Handshake negotiation
    - Certificate generation (if mTLS enabled)
    - Transport setup (Unix socket or TCP)
    - Signal handling

    Args:
        storage_dir: Directory to store KV data files. Defaults to KV_STORAGE_DIR env var or XDG_CACHE_HOME/tofusoup/kv-store.
        tls_mode: TLS mode ('disabled' or 'auto'). If None, reads from TLS_MODE environment variable.
        tls_key_type: TLS key type ('ec' or 'rsa'). If None, reads from TLS_KEY_TYPE environment variable.
        tls_curve: EC curve name. If None, reads from TLS_CURVE environment variable.
        transport: Transport type ('tcp' or 'unix'). If None, reads from PLUGIN_SERVER_TRANSPORTS environment variable.
    """
    # Read storage_dir from parameter, environment variable, or use default
    if storage_dir is None:
        storage_dir = os.getenv(ENV_KV_STORAGE_DIR) or str(get_cache_dir() / "kv-store")

    # Ensure storage directory exists
    Path(storage_dir).mkdir(parents=True, exist_ok=True)

    # Read configuration from parameters (priority) or environment (fallback)
    # Parameters come from CLI args, environment comes from subprocess env
    tls_mode = tls_mode or os.getenv("TLS_MODE", "disabled")
    tls_key_type = tls_key_type or os.getenv("TLS_KEY_TYPE", "ec")
    tls_curve = tls_curve or os.getenv("TLS_CURVE", "secp384r1")
    transport = transport or os.getenv("PLUGIN_SERVER_TRANSPORTS", "unix")

    # CRITICAL: Do NOT log to stdout before the handshake!
    # The go-plugin protocol requires the first output on stdout to be the handshake:
    # 1|1|unix|socket_path|protocol|cert_base64
    # Any other output to stdout will corrupt the handshake and break the connection.
    # All logging must go to stderr.
    logger.debug(
        "Starting KV plugin server with pyvider-rpcplugin",
        tls_mode=tls_mode,
        tls_key_type=tls_key_type,
        tls_curve=tls_curve,
        transport=transport,
        storage_dir=storage_dir,
    )

    # Create protocol and handler
    protocol = KVProtocol(storage_dir=storage_dir)
    handler = KV(storage_dir=storage_dir)

    # Build configuration for RPCPluginServer
    # pyvider-rpcplugin reads these from environment, but we can override
    config = {
        "PLUGIN_MAGIC_COOKIE_KEY": os.getenv("PLUGIN_MAGIC_COOKIE_KEY", "BASIC_PLUGIN"),
        "PLUGIN_MAGIC_COOKIE_VALUE": os.getenv("BASIC_PLUGIN", "hello"),
    }

    # Configure transport (tcp or unix socket) via rpcplugin config
    # This uses provide-foundation's configuration system
    config["PLUGIN_SERVER_TRANSPORTS"] = transport

    # Configure TLS/mTLS if enabled
    if tls_mode != "disabled":
        config["PLUGIN_AUTO_MTLS"] = True  # Enable automatic mTLS
        config["PLUGIN_TLS_KEY_TYPE"] = tls_key_type  # ec or rsa
        if tls_key_type == "ec":
            config["PLUGIN_TLS_CURVE"] = tls_curve  # secp256r1, secp384r1, secp521r1

    # Create and start the plugin server
    # RPCPluginServer handles:
    # - Handshake protocol (outputs to stdout - MUST be the only stdout output)
    # - Certificate generation (if mTLS enabled)
    # - gRPC server setup
    # - Signal handling (SIGTERM, SIGINT)
    server = RPCPluginServer(
        protocol=protocol,
        handler=handler,
        config=config,
    )

    logger.debug("RPCPluginServer created, starting serve()")
    await server.serve()


def main() -> None:
    """Entry point for standalone server (testing only)."""
    # For standalone testing without plugin protocol
    # NOT used in production - pyvider-rpcplugin mode is the default
    logger.warning("Standalone mode is deprecated - use plugin mode instead")
    logger.info(f"Starting standalone server on port {DEFAULT_GRPC_PORT}")

    # Simple standalone server for testing
    from concurrent import futures

    import grpc

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    kv = KV()
    kv_pb2_grpc.add_KVServicer_to_server(kv, server)
    server.add_insecure_port(f"[::]:{DEFAULT_GRPC_PORT}")
    server.start()

    logger.info(f"Standalone server started on port {DEFAULT_GRPC_PORT}")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down standalone server")
        server.stop(0)


if __name__ == "__main__":
    # Check if being run in plugin mode (default)
    # Plugin mode is triggered by go-plugin magic cookies in environment
    if os.getenv("PLUGIN_MAGIC_COOKIE_KEY") or os.getenv("PLUGIN_PROTOCOL_VERSIONS"):
        # Plugin mode - use pyvider-rpcplugin for proper go-plugin protocol
        logger.info("Running in plugin mode (go-plugin protocol)")
        asyncio.run(serve_plugin())
    else:
        # Standalone mode - for testing only
        logger.warning("No plugin environment detected - running in standalone mode")
        main()

# 🥣🔬🔚

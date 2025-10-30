#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TofuSoup Python KV Plugin Server

A go-plugin compatible Python server that implements the KV interface
using pyvider-rpcplugin framework. This server is compatible with
hashicorp/go-plugin protocol and can be used for cross-language testing."""

import asyncio
import os
import sys
from typing import Any

from provide.foundation import logger

from pyvider.rpcplugin.factories import plugin_server
from pyvider.rpcplugin.protocol.base import RPCPluginProtocol
from tofusoup.harness.proto.kv import kv_pb2_grpc
from tofusoup.rpc.server import KV


class KVProtocol(RPCPluginProtocol):
    """Protocol implementation for the KV service"""

    async def get_grpc_descriptors(self) -> tuple[Any, str]:
        """Return the gRPC descriptor and service name"""
        return kv_pb2_grpc, "kv.KVService"

    async def add_to_server(self, server: Any, handler: Any) -> None:
        """Add the KV service to the gRPC server"""
        kv_pb2_grpc.add_KVServicer_to_server(handler, server)
        logger.info("KV service registered with gRPC server")


async def start_kv_server() -> None:
    """Start the KV plugin server - this is the expected entry point"""
    logger.info("Starting KV plugin server...")

    # Create the KV handler
    handler = KV()

    # Create the protocol wrapper
    protocol = KVProtocol()

    # Create the plugin server using the factory function
    server = plugin_server(protocol=protocol, handler=handler)

    try:
        # This handles all the go-plugin handshake and serving
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Plugin server error: {e}")
        sys.exit(1)
    finally:
        logger.info("Plugin server shut down")


async def main() -> None:
    """Main entry point for the plugin server executable"""
    # Check for magic cookie - this indicates it's being run by go-plugin
    magic_cookie_key = os.getenv("PLUGIN_MAGIC_COOKIE_KEY", "BASIC_PLUGIN")
    magic_cookie_value = os.getenv(magic_cookie_key)
    expected_magic_value = os.getenv("PLUGIN_MAGIC_COOKIE_VALUE", "hello")

    if magic_cookie_value != expected_magic_value:
        logger.error(
            "Magic cookie mismatch. This binary is a plugin and not meant to be executed directly.",
            expected_key=magic_cookie_key,
            expected_value=expected_magic_value,
            actual_value=magic_cookie_value,
        )
        logger.error("Please execute the program that consumes these plugins.")
        sys.exit(1)

    await start_kv_server()


if __name__ == "__main__":
    asyncio.run(main())

# 🥣🔬🔚

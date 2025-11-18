#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from typing import Any

from pyvider.rpcplugin.protocol import RPCPluginProtocol

from . import kv_pb2_grpc


class KVProtocol(RPCPluginProtocol):
    """Protocol implementation for KV service using centralized proto."""

    async def get_grpc_descriptors(self) -> tuple[Any, str]:
        """Get the gRPC service descriptors."""
        return kv_pb2_grpc, "KV"

    async def add_to_server(self, server: Any, handler: Any) -> None:
        if not hasattr(handler, "Get") or not callable(handler.Get):
            raise ValueError("Invalid KV handler: missing 'Get' method")

        if not hasattr(handler, "Put") or not callable(handler.Put):
            raise ValueError("Invalid KV handler: missing 'Put' method")

        # Register the KV service implementation
        kv_pb2_grpc.add_KVServicer_to_server(handler, server)


# 🥣🔬🔚

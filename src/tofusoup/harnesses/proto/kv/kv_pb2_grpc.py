# 
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Client and server classes corresponding to protobuf-defined services."""

from typing import Never

import grpc

from . import kv_pb2 as kv__pb2

GRPC_GENERATED_VERSION = "1.73.1"
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower

    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f"The grpc package installed is at version {GRPC_VERSION},"
        + " but the generated code in kv_pb2_grpc.py depends on"
        + f" grpcio>={GRPC_GENERATED_VERSION}."
        + f" Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}"
        + f" or downgrade your generated code using grpcio-tools<={GRPC_VERSION}."
    )


class KVStub:
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel) -> None:
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Get = channel.unary_unary(
            "/proto.KV/Get",
            request_serializer=kv__pb2.GetRequest.SerializeToString,
            response_deserializer=kv__pb2.GetResponse.FromString,
            _registered_method=True,
        )
        self.Put = channel.unary_unary(
            "/proto.KV/Put",
            request_serializer=kv__pb2.PutRequest.SerializeToString,
            response_deserializer=kv__pb2.Empty.FromString,
            _registered_method=True,
        )


class KVServicer:
    """Missing associated documentation comment in .proto file."""

    def Get(self, request, context) -> Never:
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def Put(self, request, context) -> Never:
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")


def add_KVServicer_to_server(servicer, server) -> None:
    rpc_method_handlers = {
        "Get": grpc.unary_unary_rpc_method_handler(
            servicer.Get,
            request_deserializer=kv__pb2.GetRequest.FromString,
            response_serializer=kv__pb2.GetResponse.SerializeToString,
        ),
        "Put": grpc.unary_unary_rpc_method_handler(
            servicer.Put,
            request_deserializer=kv__pb2.PutRequest.FromString,
            response_serializer=kv__pb2.Empty.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler("proto.KV", rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers("proto.KV", rpc_method_handlers)


# This class is part of an EXPERIMENTAL API.
class KV:
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Get(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/proto.KV/Get",
            kv__pb2.GetRequest.SerializeToString,
            kv__pb2.GetResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True,
        )

    @staticmethod
    def Put(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/proto.KV/Put",
            kv__pb2.PutRequest.SerializeToString,
            kv__pb2.Empty.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True,
        )

# 🥣🔬🔚

#
# tofusoup/harness/proto/counter/kv_pb2_grpc.py
#
"""Client and server classes corresponding to protobuf-defined services."""


import grpc

from . import kv_pb2 as kv__pb2

GRPC_GENERATED_VERSION = "1.73.1"
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower

    _version_not_supported = first_version_is_lower(
        GRPC_VERSION, GRPC_GENERATED_VERSION
    )
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


class CounterStub:
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Get = channel.unary_unary(
            "/proto.Counter/Get",
            request_serializer=kv__pb2.GetRequest.SerializeToString,
            response_deserializer=kv__pb2.GetResponse.FromString,
            _registered_method=True,
        )
        self.Put = channel.unary_unary(
            "/proto.Counter/Put",
            request_serializer=kv__pb2.PutRequest.SerializeToString,
            response_deserializer=kv__pb2.Empty.FromString,
            _registered_method=True,
        )


class CounterServicer:
    """Missing associated documentation comment in .proto file."""

    def Get(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def Put(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")


def add_CounterServicer_to_server(servicer, server):
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
    generic_handler = grpc.method_handlers_generic_handler(
        "proto.Counter", rpc_method_handlers
    )
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers("proto.Counter", rpc_method_handlers)


# This class is part of an EXPERIMENTAL API.
class Counter:
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
            "/proto.Counter/Get",
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
            "/proto.Counter/Put",
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


class AddHelperStub:
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Sum = channel.unary_unary(
            "/proto.AddHelper/Sum",
            request_serializer=kv__pb2.SumRequest.SerializeToString,
            response_deserializer=kv__pb2.SumResponse.FromString,
            _registered_method=True,
        )


class AddHelperServicer:
    """Missing associated documentation comment in .proto file."""

    def Sum(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")


def add_AddHelperServicer_to_server(servicer, server):
    rpc_method_handlers = {
        "Sum": grpc.unary_unary_rpc_method_handler(
            servicer.Sum,
            request_deserializer=kv__pb2.SumRequest.FromString,
            response_serializer=kv__pb2.SumResponse.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "proto.AddHelper", rpc_method_handlers
    )
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers("proto.AddHelper", rpc_method_handlers)


# This class is part of an EXPERIMENTAL API.
class AddHelper:
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Sum(
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
            "/proto.AddHelper/Sum",
            kv__pb2.SumRequest.SerializeToString,
            kv__pb2.SumResponse.FromString,
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


# 🍲🥄📄🪄

#!/usr/bin/env python3
#
# tofusoup/rpc/server.py
#
from concurrent import futures
import re
import sys
import time

import grpc
from provide.foundation import logger

from tofusoup.config.defaults import DEFAULT_GRPC_PORT
from tofusoup.harness.proto.kv import kv_pb2, kv_pb2_grpc


class KV(kv_pb2_grpc.KVServicer):
    def __init__(self) -> None:
        # File-based storage pattern: /tmp/soup-kv-<key>
        self.key_pattern = re.compile(r"^[a-zA-Z0-9.-]+$")

    def _validate_key(self, key: str) -> bool:
        """Validate that key contains only allowed characters [a-zA-Z0-9.-]"""
        return bool(self.key_pattern.match(key))

    def _get_file_path(self, key: str) -> str:
        """Get the file path for a given key"""
        return f"/tmp/soup-kv-{key}"

    def Get(self, request: kv_pb2.GetRequest, context: grpc.ServicerContext) -> kv_pb2.GetResponse:
        logger.info("🔌➡️📥 Received Get request", key=request.key)

        if not self._validate_key(request.key):
            logger.error("Invalid key for Get operation", key=request.key)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(
                f'Key "{request.key}" contains invalid characters, only [a-zA-Z0-9.-] are allowed'
            )
            return kv_pb2.GetResponse()

        file_path = self._get_file_path(request.key)
        logger.debug("Retrieving value from file", key=request.key, file=file_path)

        try:
            with open(file_path, "rb") as f:
                value = f.read()
            logger.info(
                "Successfully retrieved value",
                key=request.key,
                file=file_path,
                bytes=len(value),
            )
            return kv_pb2.GetResponse(value=value)
        except FileNotFoundError:
            logger.warn("Key not found during Get operation", key=request.key, file=file_path)
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
        logger.info("🔌➡️📥 Received Put request", key=request.key)

        if not self._validate_key(request.key):
            logger.error("Invalid key for Put operation", key=request.key)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(
                f'Key "{request.key}" contains invalid characters, only [a-zA-Z0-9.-] are allowed'
            )
            return kv_pb2.Empty()

        file_path = self._get_file_path(request.key)
        logger.debug("Storing value to file", key=request.key, file=file_path)

        try:
            with open(file_path, "wb") as f:
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


def serve(server: grpc.Server) -> KV:
    servicer = KV()
    kv_pb2_grpc.add_KVServicer_to_server(servicer, server)
    return servicer


def main() -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    serve(server)
    port = server.add_insecure_port(f"[::]:{DEFAULT_GRPC_PORT}")
    logger.info(f"Server started on port {port}")
    server.start()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)


def start_kv_server(
    tls_mode: str = "disabled",
    tls_key_type: str = "ec",
    cert_file: str | None = None,
    key_file: str | None = None,
) -> None:
    """
    Start the KV plugin server with TLS configuration matching the Go implementation.
    This function is designed to work within the go-plugin framework when called by a client.
    """
    logger.info(
        "Starting KV plugin server with Python implementation",
        tls_mode=tls_mode,
        tls_key_type=tls_key_type,
        cert_file=cert_file,
        key_file=key_file,
    )

    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add the KV servicer
    serve(server)

    # Configure TLS based on mode
    if tls_mode == "disabled":
        logger.info("TLS disabled - running in insecure mode")
        port = server.add_insecure_port("[::]:0")  # Use 0 to let OS choose port
        logger.info(f"Server listening on insecure port {port}")

    elif tls_mode == "auto":
        logger.info("Auto TLS mode not fully implemented in Python server - falling back to insecure")
        logger.warning(
            "Python server does not yet support auto-generated certificates like Go's go-plugin framework"
        )
        port = server.add_insecure_port("[::]:0")
        logger.info(f"Server listening on insecure port {port} (auto TLS fallback)")

    elif tls_mode == "manual":
        if not cert_file or not key_file:
            logger.error("Manual TLS mode requires both cert_file and key_file")
            sys.exit(1)

        try:
            logger.info("Manual TLS enabled", cert_file=cert_file, key_file=key_file)

            # Load certificate and private key
            with open(cert_file, "rb") as f:
                cert_data = f.read()
            with open(key_file, "rb") as f:
                key_data = f.read()

            # Create SSL credentials
            server_credentials = grpc.ssl_server_credentials([(key_data, cert_data)])
            port = server.add_secure_port("[::]:0", server_credentials)
            logger.info(f"Server listening on secure port {port}")

        except Exception as e:
            logger.error("Failed to configure manual TLS", error=str(e))
            sys.exit(1)

    else:
        logger.error("Invalid TLS mode", mode=tls_mode)
        sys.exit(1)

    # Start the server
    server.start()
    logger.info("KV plugin server started successfully")

    try:
        # Keep the server running
        while True:
            time.sleep(86400)  # Sleep for a day
    except KeyboardInterrupt:
        logger.info("Shutting down KV plugin server")
        server.stop(0)


if __name__ == "__main__":
    main()


# 🍲🥄📄🪄

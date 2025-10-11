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
    def __init__(self, storage_dir: str = "/tmp") -> None:
        """
        Initialize KV servicer with configurable storage directory.

        Args:
            storage_dir: Directory to store KV data files. Defaults to /tmp.
        """
        self.storage_dir = storage_dir
        self.key_pattern = re.compile(r"^[a-zA-Z0-9._-]+$")
        logger.debug("Initialized KV servicer", storage_dir=storage_dir)

    def _validate_key(self, key: str) -> bool:
        """Validate that key contains only allowed characters [a-zA-Z0-9._-]"""
        return bool(self.key_pattern.match(key))

    def _get_file_path(self, key: str) -> str:
        """Get the file path for a given key"""
        return f"{self.storage_dir}/soup-kv-{key}"

    def Get(self, request: kv_pb2.GetRequest, context: grpc.ServicerContext) -> kv_pb2.GetResponse:
        logger.info("🔌➡️📥 Received Get request", key=request.key)

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
        logger.info("🔌➡️📥 Received Put request", key=request.key)

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


def serve(server: grpc.Server, storage_dir: str = "/tmp") -> KV:
    """
    Add KV servicer to gRPC server.

    Args:
        server: gRPC server instance
        storage_dir: Directory to store KV data files. Defaults to /tmp.

    Returns:
        The KV servicer instance
    """
    servicer = KV(storage_dir=storage_dir)
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
    tls_curve: str = "secp384r1",
    cert_file: str | None = None,
    key_file: str | None = None,
    storage_dir: str = "/tmp",
    output_handshake: bool = True,
) -> None:
    """
    Start the KV plugin server with TLS configuration matching the Go implementation.
    This function is designed to work within the go-plugin framework when called by a client.

    Args:
        tls_mode: TLS mode (disabled, auto, or manual)
        tls_key_type: Key type for TLS (ec or rsa)
        tls_curve: Elliptic curve for EC key type (secp256r1, secp384r1, secp521r1)
        cert_file: Path to certificate file (required for manual TLS)
        key_file: Path to private key file (required for manual TLS)
        storage_dir: Directory to store KV data files. Defaults to /tmp.
        output_handshake: If True, output go-plugin handshake to stdout
    """
    logger.info(
        "Starting KV plugin server with Python implementation",
        tls_mode=tls_mode,
        tls_key_type=tls_key_type,
        tls_curve=tls_curve,
        cert_file=cert_file,
        key_file=key_file,
        storage_dir=storage_dir,
        output_handshake=output_handshake,
    )

    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add the KV servicer with configurable storage directory
    serve(server, storage_dir=storage_dir)

    # Variables for handshake
    server_cert_pem = None

    # Configure TLS based on mode
    if tls_mode == "disabled":
        logger.info("TLS disabled - running in insecure mode")
        port = server.add_insecure_port("[::]:0")  # Use 0 to let OS choose port
        logger.info(f"Server listening on insecure port {port}")

    elif tls_mode == "auto":
        logger.info("Auto TLS enabled - generating server certificate", key_type=tls_key_type, curve=tls_curve)

        # Generate server certificate
        from provide.foundation.crypto import Certificate

        try:
            cert_obj = Certificate.create_self_signed_server_cert(
                common_name="tofusoup.rpc.server",
                organization_name="TofuSoup",
                validity_days=365,  # 1 year validity
                alt_names=["localhost", "127.0.0.1"],
                key_type="ecdsa" if tls_key_type == "ec" else tls_key_type,
                ecdsa_curve=tls_curve,
            )
            server_cert_pem = cert_obj.cert_pem
            server_key_pem = cert_obj.key_pem

            # Create SSL credentials for mTLS
            # For auto-mTLS, we accept any client cert (root_certificates=None means trust all)
            server_credentials = grpc.ssl_server_credentials(
                [(server_key_pem.encode("utf-8"), server_cert_pem.encode("utf-8"))],
                root_certificates=None,  # Accept any client certificate for auto-mTLS
                require_client_auth=True,  # mTLS: client MUST present a certificate
            )
            port = server.add_secure_port("[::]:0", server_credentials)
            logger.info(f"Server listening on secure port {port} with auto-generated certificate")

        except Exception as e:
            logger.error(f"Failed to generate auto TLS certificate: {e}")
            logger.warning("Falling back to insecure mode")
            port = server.add_insecure_port("[::]:0")
            server_cert_pem = None

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

    # Output go-plugin handshake if requested
    if output_handshake:
        import base64

        # Format: core_version|protocol_version|network|address|protocol|cert
        core_version = "1"
        protocol_version = "1"
        network = "tcp"
        address = f"127.0.0.1:{port}"
        protocol = "grpc"

        # Encode certificate for handshake (strip PEM headers and encode base64)
        cert_b64 = ""
        if server_cert_pem:
            # Remove PEM headers and whitespace
            cert_clean = server_cert_pem.replace("-----BEGIN CERTIFICATE-----", "")
            cert_clean = cert_clean.replace("-----END CERTIFICATE-----", "")
            cert_clean = cert_clean.replace("\n", "").replace("\r", "").strip()
            cert_b64 = cert_clean  # Already base64 encoded within PEM

        handshake_line = f"{core_version}|{protocol_version}|{network}|{address}|{protocol}|{cert_b64}"

        # Print to stdout (go-plugin reads this)
        print(handshake_line, flush=True)
        logger.debug(f"Handshake output: {handshake_line[:100]}...")

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

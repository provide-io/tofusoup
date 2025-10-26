#!/usr/bin/env python3
#
# tofusoup/rpc/server.py
#
from concurrent import futures
from datetime import datetime
import hashlib
import json
import os
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
        self.start_time = time.time()
        logger.debug("Initialized KV servicer", storage_dir=storage_dir)

    def _validate_key(self, key: str) -> bool:
        """Validate that key contains only allowed characters [a-zA-Z0-9._-]"""
        return bool(self.key_pattern.match(key))

    def _get_file_path(self, key: str) -> str:
        """Get the file path for a given key"""
        return f"{self.storage_dir}/kv-data-{key}"

    def _enrich_json_with_handshake(self, value_bytes: bytes, context: grpc.ServicerContext) -> bytes:
        """
        Enrich JSON value with server handshake information.

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
            value_str = value_bytes.decode('utf-8')
            json_data = json.loads(value_str)

            # Only enrich if it's a dict (not array or primitive)
            if not isinstance(json_data, dict):
                return value_bytes

            # Build server handshake information
            peer = context.peer()  # e.g., "ipv4:127.0.0.1:54321"

            server_handshake = {
                "endpoint": peer if peer else "unknown",
                "protocol_version": os.getenv("PLUGIN_PROTOCOL_VERSIONS", "1"),
                "tls_mode": os.getenv("TLS_MODE", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "received_at": round(time.time() - self.start_time, 3),
            }

            # Add TLS config if available
            tls_curve = os.getenv("TLS_CURVE")
            tls_key_type = os.getenv("TLS_KEY_TYPE")
            if tls_curve or tls_key_type:
                server_handshake["tls_config"] = {
                    "key_type": tls_key_type,
                    "curve": tls_curve,
                }

            # Add certificate fingerprint if mTLS is enabled
            server_cert = os.getenv("PLUGIN_SERVER_CERT")
            if server_cert:
                try:
                    with open(server_cert, 'rb') as f:
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
            return enriched_json.encode('utf-8')

        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            # Not JSON or not decodable - return original bytes
            logger.debug("Value is not JSON, storing as-is")
            return value_bytes
        except Exception as e:
            # Unexpected error - log and return original
            logger.warning("Failed to enrich JSON with handshake", error=str(e))
            return value_bytes

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
            # Enrich JSON values with server handshake information
            enriched_value = self._enrich_json_with_handshake(request.value, context)

            with open(file_path, "wb") as f:
                f.write(enriched_value)
            logger.info(
                "Successfully stored value",
                key=request.key,
                file=file_path,
                bytes=len(enriched_value),
                original_bytes=len(request.value),
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

            # Create SSL credentials for TLS (not full mTLS validation)
            # In go-plugin's AutoMTLS protocol, the server provides its cert to the client,
            # but the server doesn't validate the client's cert at the gRPC level.
            # The client validation happens via the go-plugin handshake mechanism instead.
            server_credentials = grpc.ssl_server_credentials(
                [(server_key_pem.encode("utf-8"), server_cert_pem.encode("utf-8"))],
                root_certificates=None,
                require_client_auth=False,  # Don't require client cert validation at gRPC level
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

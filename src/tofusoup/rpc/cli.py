#!/usr/bin/env python3
#
# tofusoup/rpc/cli.py
#
import os
import sys
from pathlib import Path

import click
import grpc

from tofusoup.config.defaults import DEFAULT_GRPC_ADDRESS

# Use correct relative import for generated protobuf modules.
from ..harness.proto.kv import kv_pb2, kv_pb2_grpc
from .server import start_kv_server
from .validation import (
    detect_server_language,
    get_compatibility_matrix,
    get_supported_curves,
    validate_curve_for_runtime,
    validate_language_pair,
    CurveNotSupportedError,
    LanguagePairNotSupportedError,
)


@click.group("rpc")
def rpc_cli() -> None:
    """Commands for interacting with gRPC services."""
    pass


@rpc_cli.command("kv-put")
@click.option("--address", default=DEFAULT_GRPC_ADDRESS, help="Address of the gRPC server.")
@click.argument("key")
@click.argument("value")
def kv_put(address: str, key: str, value: str) -> None:
    """Puts a key-value pair into the KV store."""
    try:
        with grpc.insecure_channel(address) as channel:
            stub = kv_pb2_grpc.KVStub(channel)
            # The Put RPC returns an Empty message. Its successful return is the confirmation.
            stub.Put(kv_pb2.PutRequest(key=key.encode(), value=value.encode()))
            # FIX: The Empty response has no fields. Success is implied by no exception.
            click.echo(f"Successfully put key '{key}'")
    except grpc.RpcError as e:
        click.echo(f"RPC Error: {e.details()}", err=True)


@rpc_cli.command("kv-get")
@click.option("--address", default=DEFAULT_GRPC_ADDRESS, help="Address of the gRPC server.")
@click.argument("key")
def kv_get(address: str, key: str) -> None:
    """Gets a value from the KV store by key."""
    try:
        with grpc.insecure_channel(address) as channel:
            stub = kv_pb2_grpc.KVStub(channel)
            response = stub.Get(kv_pb2.GetRequest(key=key.encode()))
            if response.value:
                click.echo(response.value.decode())
            else:
                click.echo(f"Key '{key}' not found.", err=True)
    except grpc.RpcError as e:
        click.echo(f"RPC Error: {e.details()}", err=True)


@rpc_cli.command("server-start")
@click.option(
    "--tls-mode",
    type=click.Choice(["disabled", "auto", "manual"]),
    default="disabled",
    help="TLS mode: 'disabled', 'auto', or 'manual'",
)
@click.option(
    "--tls-key-type",
    type=click.Choice(["ec", "rsa"]),
    default="ec",
    help="Key type for auto TLS: 'ec' or 'rsa'",
)
@click.option(
    "--tls-curve",
    type=click.Choice(["secp256r1", "secp384r1", "secp521r1"]),
    default="secp384r1",
    help="Elliptic curve for EC key type: 'secp256r1', 'secp384r1', or 'secp521r1'",
)
@click.option("--cert-file", help="Path to certificate file (required for manual TLS)")
@click.option("--key-file", help="Path to private key file (required for manual TLS)")
def server_start(tls_mode: str, tls_key_type: str, tls_curve: str, cert_file: str | None, key_file: str | None) -> None:
    """Starts the KV plugin server."""
    from provide.foundation import logger

    # Validate TLS configuration
    if tls_mode == "manual":
        if not cert_file or not key_file:
            click.echo(
                "Error: --cert-file and --key-file are required when --tls-mode is 'manual'",
                err=True,
            )
            sys.exit(1)
    elif tls_mode == "auto" and tls_key_type not in ["ec", "rsa"]:
        click.echo(
            "Error: --tls-key-type must be 'ec' or 'rsa' when --tls-mode is 'auto'",
            err=True,
        )
        sys.exit(1)

    # Check for magic cookie (required for go-plugin compatibility)
    magic_cookie_key = os.getenv("PLUGIN_MAGIC_COOKIE_KEY", "BASIC_PLUGIN")
    magic_cookie_value = os.getenv(magic_cookie_key)

    if not magic_cookie_value:
        logger.error(
            f"Magic cookie mismatch. Environment variable '{magic_cookie_key}' not set. "
            "This server is a plugin and not meant to be executed directly."
        )
        sys.exit(1)

    expected_value = "hello"  # This should match the Go implementation
    if magic_cookie_value != expected_value:
        logger.error(
            f"Magic cookie mismatch. Expected '{expected_value}', got '{magic_cookie_value}'. "
            "This server is a plugin and not meant to be executed directly."
        )
        sys.exit(1)

    logger.info(
        "Starting KV plugin server...",
        tls_mode=tls_mode,
        tls_key_type=tls_key_type,
        tls_curve=tls_curve,
        cert_file=cert_file,
        key_file=key_file,
    )

    # Start the server with the specified TLS configuration
    start_kv_server(
        tls_mode=tls_mode,
        tls_key_type=tls_key_type,
        tls_curve=tls_curve,
        cert_file=cert_file,
        key_file=key_file,
    )


@rpc_cli.command("validate-connection")
@click.option(
    "--client",
    type=click.Choice(["python", "go"]),
    required=True,
    help="Client language (python or go)",
)
@click.option(
    "--server",
    required=True,
    help="Path to server binary or language name (python/go)",
)
@click.option(
    "--curve",
    type=click.Choice(["secp256r1", "secp384r1", "secp521r1", "auto"]),
    default="auto",
    help="Elliptic curve to validate (default: auto)",
)
def validate_connection(client: str, server: str, curve: str) -> None:
    """
    Validate if a client-server connection is compatible.

    Checks language pair compatibility and curve support before attempting connection.

    Examples:
        soup rpc validate-connection --client python --server soup-go
        soup rpc validate-connection --client go --server /path/to/soup --curve secp384r1
    """
    from provide.foundation import output

    # Detect server language
    if server in ["python", "go"]:
        server_lang = server
        server_path_str = f"<{server} binary>"
    else:
        server_path = Path(server)
        if not server_path.exists():
            output.error(f"Server binary not found: {server}")
            output.info("Please provide a valid path to the server binary.")
            sys.exit(1)
        server_lang = detect_server_language(server_path)
        server_path_str = str(server_path)

    output.info("Validating connection compatibility...")
    output.info(f"  Client:  {client}")
    output.info(f"  Server:  {server_lang} ({server_path_str})")
    output.info(f"  Curve:   {curve}")
    output.info("")

    errors = []
    warnings = []

    # Check language pair compatibility
    try:
        validate_language_pair(client, server_path_str)
        output.success(f"✓ Language pair {client} → {server_lang} is supported")
    except LanguagePairNotSupportedError as e:
        errors.append(str(e))
        output.error(f"✗ Language pair {client} → {server_lang} is NOT supported")
        output.info("")
        output.info("Supported alternatives:")
        matrix = get_compatibility_matrix()
        for client_key, servers in matrix.items():
            for server_key, is_supported in servers.items():
                if is_supported:
                    output.success(f"  ✓ {client_key.capitalize()} → {server_key.capitalize()}")

    # Check curve compatibility for client
    if curve != "auto":
        try:
            validate_curve_for_runtime(curve, client)
            output.success(f"✓ Curve {curve} is supported by {client} client")
        except CurveNotSupportedError as e:
            errors.append(str(e))
            output.error(f"✗ Curve {curve} is NOT supported by {client} client")
            supported_curves = get_supported_curves(client)
            output.info(f"Supported curves for {client}: {', '.join(supported_curves)}")

        # Check curve compatibility for server
        try:
            validate_curve_for_runtime(curve, server_lang)
            output.success(f"✓ Curve {curve} is supported by {server_lang} server")
        except CurveNotSupportedError as e:
            errors.append(str(e))
            output.error(f"✗ Curve {curve} is NOT supported by {server_lang} server")
            supported_curves = get_supported_curves(server_lang)
            output.info(f"Supported curves for {server_lang}: {', '.join(supported_curves)}")
    else:
        output.info("ℹ  Auto curve mode - runtime will choose compatible curve")

    # Summary
    output.info("")
    if errors:
        output.error("Connection validation FAILED")
        output.info("")
        output.info("This connection will likely fail with errors:")
        for error in errors:
            output.info(f"  - {error.split('.')[0]}")  # First sentence only
        output.info("")
        output.info("See docs/rpc-compatibility-matrix.md for details.")
        sys.exit(1)
    elif warnings:
        output.warn("Connection validation passed with warnings")
        for warning in warnings:
            output.info(f"  ⚠  {warning}")
        sys.exit(0)
    else:
        output.success("Connection validation PASSED")
        output.info("This connection should work successfully.")
        sys.exit(0)


# 🍲🥄🖥️🪄

#!/usr/bin/env python3
#
# tofusoup/rpc/cli.py
#
import os
import sys

import click
import grpc

# Use correct relative import for generated protobuf modules.
from ..harness.proto.kv import kv_pb2, kv_pb2_grpc
from .server import start_kv_server


@click.group("rpc")
def rpc_cli():
    """Commands for interacting with gRPC services."""
    pass


@rpc_cli.command("kv-put")
@click.option(
    "--address", default="localhost:50051", help="Address of the gRPC server."
)
@click.argument("key")
@click.argument("value")
def kv_put(address: str, key: str, value: str):
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
@click.option(
    "--address", default="localhost:50051", help="Address of the gRPC server."
)
@click.argument("key")
def kv_get(address: str, key: str):
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
@click.option("--cert-file", help="Path to certificate file (required for manual TLS)")
@click.option("--key-file", help="Path to private key file (required for manual TLS)")
def server_start(
    tls_mode: str, tls_key_type: str, cert_file: str | None, key_file: str | None
):
    """Starts the KV plugin server."""
    from pyvider.telemetry import logger

    # Validate TLS configuration
    if tls_mode == "manual":
        if not cert_file or not key_file:
            click.echo(
                "Error: --cert-file and --key-file are required when --tls-mode is 'manual'",
                err=True,
            )
            sys.exit(1)
    elif tls_mode == "auto":
        if tls_key_type not in ["ec", "rsa"]:
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
        cert_file=cert_file,
        key_file=key_file,
    )

    # Start the server with the specified TLS configuration
    start_kv_server(
        tls_mode=tls_mode,
        tls_key_type=tls_key_type,
        cert_file=cert_file,
        key_file=key_file,
    )


# 🍲🥄🖥️🪄

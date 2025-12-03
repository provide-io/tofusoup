#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import os
from pathlib import Path
import sys

import click
import grpc

from tofusoup.config.defaults import DEFAULT_GRPC_ADDRESS

# Use correct relative import for generated protobuf modules.
from ..harness.proto.kv import kv_pb2, kv_pb2_grpc
from .server import serve_plugin
from .validation import (
    CurveNotSupportedError,
    LanguagePairNotSupportedError,
    detect_server_language,
    get_compatibility_matrix,
    get_supported_curves,
    normalize_curve_name,
    validate_curve_for_runtime,
    validate_language_pair,
)


@click.group("rpc")
def rpc_cli() -> None:
    """Commands for interacting with gRPC services."""
    pass


@click.group("kv")
def kv_cli() -> None:
    """Commands for the Key-Value store."""
    pass


@kv_cli.command("put")
@click.option("--address", default=DEFAULT_GRPC_ADDRESS, help="Address of the gRPC server.")
@click.argument("key")
@click.argument("value")
def kv_put(address: str, key: str, value: str) -> None:
    """Puts a key-value pair into the KV store."""
    try:
        with grpc.insecure_channel(address) as channel:
            stub = kv_pb2_grpc.KVStub(channel)
            stub.Put(kv_pb2.PutRequest(key=key.encode(), value=value.encode()))
            click.echo(f"Successfully put key '{key}'")
    except grpc.RpcError as e:
        click.echo(f"RPC Error: {e.details()}", err=True)


@kv_cli.command("get")
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


@kv_cli.command("server")
@click.option(
    "--tls-mode",
    type=click.Choice(["disabled", "auto"]),
    default="disabled",
    help="TLS mode: 'disabled' or 'auto' (auto-mTLS with certificate generation)",
)
@click.option(
    "--tls-key-type",
    type=click.Choice(["ec", "rsa"]),
    default="ec",
    help="Key type for auto TLS: 'ec' or 'rsa'",
)
@click.option(
    "--tls-curve",
    type=click.Choice(
        ["secp256r1", "secp384r1", "secp521r1", "P-256", "P-384", "P-521", "p256", "p384", "p521"]
    ),
    default="secp384r1",
    help="Elliptic curve for EC key type: 'secp256r1'/'P-256', 'secp384r1'/'P-384', or 'secp521r1'/'P-521'",
)
@click.option(
    "--transport",
    type=click.Choice(["tcp", "unix"]),
    default="unix",
    help="Transport type: 'tcp' (TCP/IP) or 'unix' (Unix domain socket)",
)
def server_start(tls_mode: str, tls_key_type: str, tls_curve: str, transport: str) -> None:
    """Starts the KV plugin server using pyvider-rpcplugin.

    This server uses the go-plugin protocol and requires magic cookie environment variables:
    - PLUGIN_MAGIC_COOKIE_KEY (default: BASIC_PLUGIN)
    - BASIC_PLUGIN=hello (or value matching the key)

    TLS certificates are automatically generated when --tls-mode is 'auto'.
    """
    import asyncio

    from provide.foundation import logger

    tls_curve = normalize_curve_name(tls_curve)

    # Validate TLS configuration
    if tls_mode == "auto" and tls_key_type not in ["ec", "rsa"]:
        click.echo(
            "Error: --tls-key-type must be 'ec' or 'rsa' when --tls-mode is 'auto'",
            err=True,
        )
        sys.exit(1)

    # Check for required magic cookie environment variables
    magic_cookie_key = os.getenv("PLUGIN_MAGIC_COOKIE_KEY", "BASIC_PLUGIN")
    magic_cookie_value = os.getenv(magic_cookie_key)

    if not magic_cookie_value:
        logger.error(
            f"Magic cookie mismatch. Environment variable '{magic_cookie_key}' not set. "
            "This server is a plugin and not meant to be executed directly."
        )
        sys.exit(1)

    expected_value = "hello"
    if magic_cookie_value != expected_value:
        logger.error(
            f"Magic cookie mismatch. Expected '{expected_value}', got '{magic_cookie_value}'. "
            "This server is a plugin and not meant to be executed directly."
        )
        sys.exit(1)

    logger.info(
        "Starting KV plugin server with pyvider-rpcplugin...",
        tls_mode=tls_mode,
        tls_key_type=tls_key_type,
        tls_curve=tls_curve,
        transport=transport,
    )

    # Run async server with TLS and transport configuration from CLI args
    asyncio.run(
        serve_plugin(
            tls_mode=tls_mode,
            tls_key_type=tls_key_type,
            tls_curve=tls_curve,
            transport=transport,
        )
    )


@click.group("validate")
def validate_cli() -> None:
    """Commands for validation."""
    pass


@validate_cli.command("connection")
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
    """Validate if a client-server connection is compatible."""
    from provide.foundation import pout

    server_lang, server_path_str = _detect_server_language(server)

    pout("Validating connection compatibility...", color="cyan", bold=True)
    pout(f"  Client:  {client}")
    pout(f"  Server:  {server_lang} ({server_path_str})")
    pout(f"  Curve:   {curve}")
    pout("")

    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(_validate_language_pair_with_output(client, server_lang, server_path_str))
    errors.extend(_validate_curve_compatibility_with_output(curve, client, server_lang))

    _print_validation_summary(errors, warnings)


def _detect_server_language(server: str) -> tuple[str, str]:
    from provide.foundation import perr, pout

    if server in ["python", "go"]:
        return server, f"<{server} binary>"

    server_path = Path(server)
    if not server_path.exists():
        perr(f"Server binary not found: {server}", color="red", bold=True)
        pout("Please provide a valid path to the server binary.")
        sys.exit(1)

    server_lang = detect_server_language(server_path)
    return server_lang, str(server_path)


def _validate_language_pair_with_output(client: str, server_lang: str, server_path_str: str) -> list[str]:
    from provide.foundation import perr, pout

    errors = []

    try:
        validate_language_pair(client, server_path_str)
        pout(f"✓ Language pair {client} → {server_lang} is supported", color="green")
    except LanguagePairNotSupportedError as e:
        errors.append(str(e))
        perr(f"✗ Language pair {client} → {server_lang} is NOT supported", color="red", bold=True)
        pout("")
        pout("Supported alternatives:", color="cyan")
        matrix = get_compatibility_matrix()
        for client_key, servers in matrix.items():
            for server_key, is_supported in servers.items():
                if is_supported:
                    pout(f"  ✓ {client_key.capitalize()} → {server_key.capitalize()}", color="green")

    return errors


def _validate_curve_compatibility_with_output(curve: str, client: str, server_lang: str) -> list[str]:
    from provide.foundation import perr, pout

    errors = []

    if curve == "auto":
        pout("i  Auto curve mode - runtime will choose compatible curve", color="blue")
        return errors

    try:
        validate_curve_for_runtime(curve, client)
        pout(f"✓ Curve {curve} is supported by {client} client", color="green")
    except CurveNotSupportedError as e:
        errors.append(str(e))
        perr(f"✗ Curve {curve} is NOT supported by {client} client", color="red", bold=True)
        supported_curves = get_supported_curves(client)
        pout(f"Supported curves for {client}: {', '.join(supported_curves)}")

    try:
        validate_curve_for_runtime(curve, server_lang)
        pout(f"✓ Curve {curve} is supported by {server_lang} server", color="green")
    except CurveNotSupportedError as e:
        errors.append(str(e))
        perr(f"✗ Curve {curve} is NOT supported by {server_lang} server", color="red", bold=True)
        supported_curves = get_supported_curves(server_lang)
        pout(f"Supported curves for {server_lang}: {', '.join(supported_curves)}")

    return errors


def _print_validation_summary(errors: list[str], warnings: list[str]) -> None:
    from provide.foundation import perr, pout

    pout("")

    if errors:
        perr("Connection validation FAILED", color="red", bold=True)
        pout("")
        pout("This connection will likely fail with errors:", color="yellow")
        for error in errors:
            pout(f"  - {error.split('.')[0]}")
        pout("")
        pout("See docs/rpc-compatibility-matrix.md for details.", color="cyan")
        sys.exit(1)
    elif warnings:
        pout("Connection validation passed with warnings", color="yellow", bold=True)
        for warning in warnings:
            pout(f"  ⚠  {warning}", color="yellow")
        sys.exit(0)
    else:
        pout("Connection validation PASSED", color="green", bold=True)
        pout("This connection should work successfully.", color="green")
        sys.exit(0)


rpc_cli.add_command(kv_cli)
rpc_cli.add_command(validate_cli)

# 🥣🔬🔚

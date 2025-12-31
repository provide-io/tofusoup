#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Stock service CLI commands for direct gRPC testing.
Supports multiple language implementations without plugin handshake."""

from pathlib import Path
import subprocess
import sys

import click
from provide.foundation import logger
from provide.foundation.process import run as run_command
from rich.console import Console
from rich.table import Table

from tofusoup.config.defaults import (
    DEFAULT_CLIENT_LANGUAGE,
    DEFAULT_GRPC_ADDRESS,
    DEFAULT_GRPC_PORT,
    DEFAULT_TLS_MODE,
)

console = Console()

# Supported languages for Stock implementations
SUPPORTED_LANGUAGES = [
    "go",
    "python",
    "java",
    "ruby",
    "csharp",
    "rust",
    "cpp",
    "nodejs",
]


def get_stock_binary_path(language: str, role: str) -> Path:
    """
    Get the path to the stock binary for a given language and role.

    Note: Paths are currently hardcoded. Future enhancement will read from soup.toml configuration.
    """
    base_dir = Path(__file__).parent.parent.parent.parent / "direct" / language

    binary_map = {
        "go": base_dir / "bin" / f"stock-{role}",
        "python": base_dir / f"stock_{role}.py",
        "java": base_dir / "target" / f"stock-{role}.jar",
        "ruby": base_dir / f"stock_{role}.rb",
        "csharp": base_dir / "bin" / f"Stock{role.title()}",
        "rust": base_dir / "target" / "release" / f"stock-{role}",
        "cpp": base_dir / "build" / f"stock_{role}",
        "nodejs": base_dir / f"stock-{role}.js",
    }

    return binary_map.get(language, base_dir / f"stock-{role}")


@click.group("stock")
def stock_cli() -> None:
    """Direct gRPC Stock service commands (no plugin handshake)."""


@stock_cli.command("server")
@click.argument("language", type=click.Choice(SUPPORTED_LANGUAGES))
@click.option("--port", default=DEFAULT_GRPC_PORT, help="Port to listen on")
@click.option("--tls-mode", type=click.Choice(["none", "auto", "manual"]), default=DEFAULT_TLS_MODE)
@click.option("--cert-file", help="TLS certificate file (manual mode)")
@click.option("--key-file", help="TLS key file (manual mode)")
def server_cmd(
    language: str,
    port: int,
    tls_mode: str,
    cert_file: str | None,
    key_file: str | None,
) -> None:
    """Start a Stock server in the specified language."""
    binary_path = get_stock_binary_path(language, "server")

    if not binary_path.exists():
        console.print(f"[red]Error: {language} server not found at {binary_path}[/red]")
        console.print(f"[yellow]Run 'soup harness build stock-{language}' first[/yellow]")
        sys.exit(1)

    cmd = [str(binary_path), "--port", str(port), "--tls-mode", tls_mode]

    if tls_mode == "manual":
        if not cert_file or not key_file:
            console.print("[red]Error: --cert-file and --key-file required for manual TLS[/red]")
            sys.exit(1)
        cmd.extend(["--cert-file", cert_file, "--key-file", key_file])

    console.print(f"[green]Starting {language} Stock server on port {port}...[/green]")
    logger.info("Starting Stock server", language=language, port=port, tls_mode=tls_mode)

    try:
        # For interpreted languages, we might need to prepend the interpreter
        if language == "python":
            cmd = ["python3", *cmd]
        elif language == "ruby":
            cmd = ["ruby", *cmd]
        elif language == "nodejs":
            cmd = ["node", *cmd]
        elif language == "java":
            cmd = ["java", "-jar", *cmd]

        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error running server: {e}[/red]")
        sys.exit(1)


def _get_client_cmd(
    language: str, operation: str, args: tuple[str, ...], server: str, tls: bool, ca_file: str | None
) -> list[str]:
    binary_path = get_stock_binary_path(language, "client")

    if not binary_path.exists():
        console.print(f"[red]Error: {language} client not found at {binary_path}[/red]")
        console.print(f"[yellow]Run 'soup harness build stock-{language}' first[/yellow]")
        sys.exit(1)

    cmd = [str(binary_path), operation, "--server", server]

    if tls:
        cmd.append("--tls")
        if ca_file:
            cmd.extend(["--ca-file", ca_file])

    cmd.extend(args)

    if language == "python":
        return ["python3", *cmd]
    if language == "ruby":
        return ["ruby", *cmd]
    if language == "nodejs":
        return ["node", *cmd]
    if language == "java":
        return ["java", "-jar", *cmd]

    return cmd


def _run_client_cmd(cmd: list[str], language: str, operation: str, server: str) -> None:
    logger.info("Running Stock client", language=language, operation=operation, server=server)
    try:
        result = run_command(cmd, capture_output=True, text=True, check=False)
        if result.stdout:
            console.print(result.stdout.strip())
        if result.stderr and result.returncode != 0:
            print(f"[red]{result.stderr.strip()}[/red]", file=sys.stderr)
            sys.exit(result.returncode)
    except Exception as e:
        console.print(f"[red]Error running client: {e}[/red]")
        sys.exit(1)


@stock_cli.command("client")
@click.argument("language", type=click.Choice(SUPPORTED_LANGUAGES))
@click.argument("operation", type=click.Choice(["get", "put", "monitor", "inventory"]))
@click.argument("args", nargs=-1)
@click.option("--server", default=DEFAULT_GRPC_ADDRESS, help="Server address")
@click.option("--tls/--no-tls", default=False, help="Use TLS")
@click.option("--ca-file", help="CA certificate file for TLS")
def client_cmd(
    language: str,
    operation: str,
    args: tuple[str, ...],
    server: str,
    tls: bool,
    ca_file: str | None,
) -> None:
    """Run a Stock client operation in the specified language."""
    cmd = _get_client_cmd(language, operation, args, server, tls, ca_file)
    _run_client_cmd(cmd, language, operation, server)


@stock_cli.command("matrix")
@click.option("--client", multiple=True, help="Client languages to test")
@click.option("--server", multiple=True, help="Server languages to test")
@click.option("--quick", is_flag=True, help="Run quick subset of tests")
def matrix_cmd(client: tuple[str, ...], server: tuple[str, ...], quick: bool) -> None:
    """Run Stock service matrix tests across languages."""
    clients = list(client) if client else SUPPORTED_LANGUAGES
    servers = list(server) if server else SUPPORTED_LANGUAGES

    if quick:
        # Quick mode: just test a few key combinations
        clients = ["go", "python", "java"]
        servers = ["go", "python"]

    total = len(clients) * len(servers)

    table = Table(title="Stock Service Test Matrix")
    table.add_column("Client", style="cyan")
    table.add_column("Server", style="magenta")
    table.add_column("Status", style="green")

    console.print(f"\n[bold]Running {total} test combinations...[/bold]\n")

    passed = 0
    for server_lang in servers:
        for client_lang in clients:
            # NOTE: Test matrix functionality not yet implemented
            # This command shows the test plan but doesn't execute tests
            # Use individual 'client' and 'server' commands for actual testing
            status = "⏸️  Not Implemented"
            table.add_row(client_lang, server_lang, status)

    console.print(table)
    console.print(f"\n[bold]Results: {passed}/{total} passed[/bold]")


# Convenience commands that map to the original KV interface
@stock_cli.command("get")
@click.argument("key")
@click.option("--client", default=DEFAULT_CLIENT_LANGUAGE, help="Client language to use")
@click.option("--server", default=DEFAULT_GRPC_ADDRESS, help="Server address")
def get_cmd(key: str, client: str, server: str) -> None:
    """Get a value using Stock service (convenience wrapper)."""
    ctx = click.get_current_context()
    ctx.invoke(client_cmd, language=client, operation="get", args=(key,), server=server)


@stock_cli.command("put")
@click.argument("key")
@click.argument("value")
@click.option("--client", default=DEFAULT_CLIENT_LANGUAGE, help="Client language to use")
@click.option("--server", default=DEFAULT_GRPC_ADDRESS, help="Server address")
def put_cmd(key: str, value: str, client: str, server: str) -> None:
    """Put a key-value pair using Stock service (convenience wrapper)."""
    ctx = click.get_current_context()
    ctx.invoke(client_cmd, language=client, operation="put", args=(key, value), server=server)


# 🥣🔬🔚

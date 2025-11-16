#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import os
import pathlib
import sys

from attrs import evolve
import click
from provide.foundation import LoggingConfig, TelemetryConfig, get_hub, logger
from rich import print as rich_print_direct
from rich.tree import Tree

from tofusoup.common.config import TofuSoupConfig, TofuSoupConfigError, load_tofusoup_config
from tofusoup.common.lazy_group import LazyGroup
from tofusoup.common.rich_utils import build_rich_tree_from_dict
from tofusoup.common.utils import get_cache_dir
from tofusoup.config.defaults import LOG_LEVELS

# CRITICAL: Foundation logger uses stderr by default (good for go-plugin compatibility)
# stdout is reserved for the plugin handshake protocol
# NOTE: We delay Foundation initialization until entry_point() to avoid event loop conflicts in plugin mode
hub = get_hub()

LAZY_COMMANDS = {
    "sui": ("tofusoup.browser.cli", "sui_cli"),
    "registry": ("tofusoup.registry.cli", "registry_cli"),
    "cty": ("tofusoup.cty.cli", "cty_cli"),
    "hcl": ("tofusoup.hcl.cli", "hcl_cli"),
    "harness": ("tofusoup.harness.cli", "harness_cli"),
    "rpc": ("tofusoup.rpc.cli", "rpc_cli"),
    "state": ("tofusoup.state", "state_cli"),
    "stir": ("tofusoup.stir", "stir_cli"),
    "test": ("tofusoup.testing.cli", "test_cli"),
    "wire": ("tofusoup.wire.cli", "wire"),
}


@click.group(
    name="tofusoup",
    invoke_without_command=True,
    cls=LazyGroup,
    lazy_commands=LAZY_COMMANDS,
)
@click.pass_context
@click.version_option(package_name="tofusoup")
@click.option("--verbose/--no-verbose", default=False, help="Enable verbose output.")
@click.option(
    "--log-level",
    type=click.Choice(LOG_LEVELS, case_sensitive=False),
    default=None,
    help="Set the logging level.",
)
@click.option(
    "--config-file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    default=None,
    help="Path to a specific TofuSoup configuration file.",
)
def main_cli(ctx: click.Context, verbose: bool, log_level: str | None, config_file: str | None) -> None:
    ctx.obj = ctx.obj or {}

    final_log_level = "DEBUG" if verbose else log_level
    if final_log_level:
        updated_config = TelemetryConfig(
            service_name="tofusoup-cli",
            logging=LoggingConfig(default_level=final_log_level.upper()),
        )
        hub.initialize_foundation(config=updated_config)
        logger.debug(f"Log level set to {final_log_level.upper()} by CLI option.")

    # Start from current working directory to find project root
    project_root_path = pathlib.Path.cwd()
    while project_root_path != project_root_path.parent:
        if (project_root_path / "pyproject.toml").exists():
            break
        project_root_path = project_root_path.parent
    else:
        # If no pyproject.toml found, use current directory as fallback
        project_root_path = pathlib.Path.cwd()
        logger.debug("No pyproject.toml found in tree, using current directory as project root")

    try:
        loaded_config = load_tofusoup_config(project_root_path, explicit_config_file=config_file)
    except TofuSoupConfigError as e:
        # Config errors are not fatal - some commands don't need config
        logger.debug(f"Configuration not loaded: {e}")
        loaded_config = {}
    ctx.obj["TOFUSOUP_CONFIG"] = loaded_config
    ctx.obj["PROJECT_ROOT"] = project_root_path

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@click.group("config")
def config_cli() -> None:
    """Commands for TofuSoup configuration management."""
    pass


@config_cli.command("show")
@click.pass_context
def show_config_command(ctx: click.Context) -> None:
    """Displays the currently loaded TofuSoup configuration."""
    loaded_config = ctx.obj.get("TOFUSOUP_CONFIG", {})
    if not loaded_config:
        rich_print_direct("[yellow]No TofuSoup configuration loaded or configuration is empty.[/yellow]")
        return

    config_tree = Tree("🍲 [bold green]Loaded TofuSoup Configuration[/bold green]")
    build_rich_tree_from_dict(config_tree, loaded_config, "Config Root")
    rich_print_direct(config_tree)


main_cli.add_command(config_cli)


def entry_point() -> None:
    """
    CLI entry point with automatic plugin server detection.

    If invoked with the plugin magic cookie in the environment and no arguments,
    automatically starts as an RPC plugin server (for go-plugin compatibility).
    """
    # Check if we're being invoked as a plugin server BEFORE initializing Foundation
    magic_cookie_key = os.getenv("PLUGIN_MAGIC_COOKIE_KEY", "BASIC_PLUGIN")
    magic_cookie_value = os.getenv(magic_cookie_key)

    # Check if invoked as plugin server:
    # 1. Magic cookie present + no args (terraform/go-plugin standard)
    # 2. Magic cookie present + "rpc server-start" args (our Go client calls it this way)
    is_plugin_mode = magic_cookie_value and (
        len(sys.argv) == 1 or (len(sys.argv) == 3 and sys.argv[1] == "rpc" and sys.argv[2] == "server-start")
    )

    if is_plugin_mode:
        # Initialize Foundation for plugin mode with minimal logging
        # Do NOT create an event loop - let asyncio.run() handle that
        plugin_config = TelemetryConfig(
            service_name="tofusoup-plugin",
            logging=LoggingConfig(default_level="ERROR"),  # Minimal logging in plugin mode
        )
        hub.initialize_foundation(config=plugin_config)

        # Debug: Log key environment variables to diagnose go-plugin behavior
        # Debug logging - also write to file for visibility
        debug_log_path = get_cache_dir() / "logs" / "plugin_debug.log"
        debug_log_path.parent.mkdir(parents=True, exist_ok=True)
        with debug_log_path.open("a") as f:
            import datetime

            f.write(f"\n\n=== Plugin start: {datetime.datetime.now()} ===\n")
            f.write(f"PLUGIN_AUTO_MTLS = {os.getenv('PLUGIN_AUTO_MTLS')}\n")
            f.write(f"Magic cookie key = {magic_cookie_key}\n")
            f.write(f"Magic cookie value = {magic_cookie_value}\n")
            f.write(f"All PLUGIN_* env vars: {[k for k in os.environ if 'PLUGIN' in k]}\n")

        logger.debug(
            "Plugin mode detected",
            plugin_auto_mtls=os.getenv("PLUGIN_AUTO_MTLS"),
            magic_cookie_key=magic_cookie_key,
            magic_cookie_value=magic_cookie_value,
            all_plugin_env_vars={k: v for k, v in os.environ.items() if "PLUGIN" in k},
        )

        # Start the RPC server using pyvider-rpcplugin infrastructure
        import asyncio

        from pyvider.rpcplugin.server import RPCPluginServer
        from tofusoup.harness.proto.kv import KVProtocol
        from tofusoup.rpc.server import KV

        storage_dir = os.getenv("KV_STORAGE_DIR") or str(get_cache_dir() / "kv-store")

        # Create KV handler
        handler = KV(storage_dir=storage_dir)

        # Create protocol wrapper
        protocol = KVProtocol()

        # Configure the RPC plugin server with the magic cookie from Go client
        server_config = {
            "PLUGIN_MAGIC_COOKIE_KEY": magic_cookie_key,
            "PLUGIN_MAGIC_COOKIE_VALUE": magic_cookie_value,
        }

        # When AutoMTLS is enabled, force TCP transport (Go client expects TCP+TLS, not Unix sockets)
        if os.getenv("PLUGIN_AUTO_MTLS", "").lower() == "true":
            server_config["PLUGIN_SERVER_TRANSPORTS"] = ["tcp"]  # Must be a list
            logger.debug("AutoMTLS enabled, forcing TCP transport")

        logger.debug("Creating RPCPluginServer", server_config=server_config)

        # Create server without explicit transport (let it auto-negotiate)
        # This matches pyvider's pattern and allows proper transport negotiation
        server = RPCPluginServer(protocol=protocol, handler=handler, config=server_config)

        logger.debug("RPCPluginServer created, starting serve()")

        # Start the server - this will block until shutdown
        try:
            with debug_log_path.open("a") as f:
                f.write("About to start server.serve()\n")

            # RPCPluginServer may have created a loop during initialization
            # Get or create an event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    with debug_log_path.open("a") as f:
                        f.write("Previous loop was closed, created new one\n")
                else:
                    with debug_log_path.open("a") as f:
                        f.write("Using existing event loop\n")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                with debug_log_path.open("a") as f:
                    f.write("Created new event loop\n")

            # Run the server
            try:
                loop.run_until_complete(server.serve())
                with debug_log_path.open("a") as f:
                    f.write("Server.serve() completed normally\n")
            finally:
                loop.close()

            sys.exit(0)
        except KeyboardInterrupt:
            logger.info("Plugin server interrupted by user")
            with debug_log_path.open("a") as f:
                f.write("KeyboardInterrupt\n")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Plugin server failed to start: {e}", exc_info=True)
            with debug_log_path.open("a") as f:
                import traceback as tb

                f.write(f"Exception: {e!s}\n")
                f.write(tb.format_exc())
            import traceback

            traceback.print_exc()
            sys.exit(1)

    # Normal CLI invocation - initialize Foundation for CLI mode
    # Load TofuSoup configuration from environment
    tofusoup_config = TofuSoupConfig.from_env()  # type: ignore[attr-defined]

    # Get base telemetry config from environment
    base_telemetry = TelemetryConfig.from_env()

    # Merge with TofuSoup-specific settings
    telemetry_config = evolve(
        base_telemetry,
        service_name="tofusoup-cli",
        logging=evolve(
            base_telemetry.logging,
            default_level=tofusoup_config.log_level,
        ),
    )

    # Initialize Foundation with merged config
    hub.initialize_foundation(config=telemetry_config)
    main_cli(obj={})


if __name__ == "__main__":
    entry_point()

# 🥣🔬🔚

#!/usr/bin/env python3
#
# tofusoup/cli.py
#
import os
import pathlib
import sys

import click
from provide.foundation import LoggingConfig, TelemetryConfig, get_hub, logger
from rich import print as rich_print_direct
from rich.tree import Tree

from tofusoup.common.config import TofuSoupConfigError, load_tofusoup_config
from tofusoup.common.lazy_group import LazyGroup
from tofusoup.common.rich_utils import build_rich_tree_from_dict
from tofusoup.config.defaults import DEFAULT_LOG_LEVEL, ENV_TOFUSOUP_LOG_LEVEL, LOG_LEVELS

# CRITICAL: Configure Foundation logger to use stderr for go-plugin compatibility
# stdout is reserved for the plugin handshake protocol
telemetry_config = TelemetryConfig(
    service_name="tofusoup-cli",
    logging=LoggingConfig(
        default_level=os.environ.get(ENV_TOFUSOUP_LOG_LEVEL, DEFAULT_LOG_LEVEL).upper(),
        stream=sys.stderr,  # Force all logging to stderr
    ),
)
hub = get_hub()
hub.initialize_foundation(config=telemetry_config)

LAZY_COMMANDS = {
    "sui": ("tofusoup.browser.cli", "sui_cli"),
    "registry": ("tofusoup.registry.cli", "registry_cli"),
    "cty": ("tofusoup.cty.cli", "cty_cli"),
    "hcl": ("tofusoup.hcl.cli", "hcl_cli"),
    "harness": ("tofusoup.harness.cli", "harness_cli"),
    # Package command removed - packaging is handled by separate tools
    "provider": ("tofusoup.provider.cli", "provider_cli"),
    "rpc": ("tofusoup.rpc.cli", "rpc_cli"),
    "state": ("tofusoup.state", "state_cli"),
    "stir": ("tofusoup.stir", "stir_cli"),
    "test": ("tofusoup.testing.cli", "test_cli"),
    "wire": ("tofusoup.wire.cli", "wire"),
    # Note: plating command has been moved to separate plating package
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
        raise FileNotFoundError("Could not determine project root containing 'pyproject.toml'.")

    try:
        loaded_config = load_tofusoup_config(project_root_path, explicit_config_file=config_file)
    except TofuSoupConfigError as e:
        logger.error(f"Configuration Error: {e}. Aborting.")
        sys.exit(1)
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
    # Check if we're being invoked as a plugin server
    magic_cookie_key = os.getenv("PLUGIN_MAGIC_COOKIE_KEY", "BASIC_PLUGIN")
    magic_cookie_value = os.getenv(magic_cookie_key)

    # If magic cookie is present and we have no command-line arguments (or just the script name)
    # then we're being invoked as a plugin by go-plugin framework
    if magic_cookie_value and len(sys.argv) == 1:
        # Minimize logging for plugin mode (already using stderr from top of file)
        updated_config = TelemetryConfig(
            service_name="tofusoup-plugin",
            logging=LoggingConfig(default_level="ERROR"),  # Minimize logging
        )
        hub.initialize_foundation(config=updated_config)

        # Start the RPC server using pyvider-rpcplugin infrastructure
        import asyncio
        from tofusoup.harness.proto.kv import KVProtocol
        from tofusoup.rpc.server import KV
        from pyvider.rpcplugin.factories import plugin_server

        storage_dir = os.getenv("KV_STORAGE_DIR", "/tmp")

        # Create KV handler
        handler = KV(storage_dir=storage_dir)

        # Create protocol wrapper
        protocol = KVProtocol()

        # Create server using pyvider factory
        # This handles handshake, mTLS, and all go-plugin protocol automatically
        server = plugin_server(
            protocol=protocol,
            handler=handler,
            transport="tcp",  # Use TCP for compatibility
        )

        # Start the server - this will block until shutdown
        try:
            asyncio.run(server.serve())
            sys.exit(0)
        except Exception as e:
            logger.error(f"Plugin server failed to start: {e}")
            sys.exit(1)

    # Normal CLI invocation
    main_cli(obj={})


if __name__ == "__main__":
    entry_point()


# 🍲🥄🖥️🪄

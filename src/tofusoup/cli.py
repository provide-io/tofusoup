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

# CRITICAL: Foundation logger uses stderr by default (good for go-plugin compatibility)
# stdout is reserved for the plugin handshake protocol
telemetry_config = TelemetryConfig(
    service_name="tofusoup-cli",
    logging=LoggingConfig(
        default_level=os.environ.get(ENV_TOFUSOUP_LOG_LEVEL, DEFAULT_LOG_LEVEL).upper(),
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

    # Check if invoked as plugin server:
    # 1. Magic cookie present + no args (terraform/go-plugin standard)
    # 2. Magic cookie present + "rpc server-start" args (our Go client calls it this way)
    is_plugin_mode = magic_cookie_value and (
        len(sys.argv) == 1 or
        (len(sys.argv) == 3 and sys.argv[1] == "rpc" and sys.argv[2] == "server-start")
    )

    if is_plugin_mode:
        # Minimize logging for plugin mode (already using stderr from top of file)
        updated_config = TelemetryConfig(
            service_name="tofusoup-plugin",
            logging=LoggingConfig(default_level="DEBUG"),  # Debug logging for now
        )
        hub.initialize_foundation(config=updated_config)

        # Debug: Log key environment variables to diagnose go-plugin behavior
        # Debug logging - also write to file for visibility
        debug_log_path = "/tmp/tofusoup_plugin_debug.log"
        with open(debug_log_path, "a") as f:
            import datetime
            f.write(f"\n\n=== Plugin start: {datetime.datetime.now()} ===\n")
            f.write(f"PLUGIN_AUTO_MTLS = {os.getenv('PLUGIN_AUTO_MTLS')}\n")
            f.write(f"Magic cookie key = {magic_cookie_key}\n")
            f.write(f"Magic cookie value = {magic_cookie_value}\n")
            f.write(f"All PLUGIN_* env vars: {[k for k in os.environ.keys() if 'PLUGIN' in k]}\n")

        logger.debug("Plugin mode detected",
                     plugin_auto_mtls=os.getenv('PLUGIN_AUTO_MTLS'),
                     magic_cookie_key=magic_cookie_key,
                     magic_cookie_value=magic_cookie_value,
                     all_plugin_env_vars={k: v for k, v in os.environ.items() if 'PLUGIN' in k})

        # Start the RPC server using pyvider-rpcplugin infrastructure
        import asyncio
        from tofusoup.harness.proto.kv import KVProtocol
        from tofusoup.rpc.server import KV
        from pyvider.rpcplugin.server import RPCPluginServer

        storage_dir = os.getenv("KV_STORAGE_DIR", "/tmp")

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
            with open(debug_log_path, "a") as f:
                f.write("About to start server.serve()\n")

            # Use asyncio.run() which creates a new event loop
            # Foundation's initialization should not create a running loop in plugin mode
            try:
                logger.debug("About to call asyncio.run(server.serve())")
                asyncio.run(server.serve())
                logger.debug("Server.serve() completed normally")
                with open(debug_log_path, "a") as f:
                    f.write("Server.serve() completed normally\n")
            except RuntimeError as e:
                if "attached to a different loop" in str(e):
                    # Fallback: Try getting the existing loop if asyncio.run() fails
                    logger.warning("Event loop conflict detected, trying alternative approach", error=str(e))
                    with open(debug_log_path, "a") as f:
                        f.write(f"Event loop conflict: {str(e)}\n")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    logger.debug("Running serve() with new event loop")
                    loop.run_until_complete(server.serve())
                    loop.close()
                    logger.debug("Serve() completed with fallback loop")
                    with open(debug_log_path, "a") as f:
                        f.write("Serve() completed with fallback loop\n")
                else:
                    logger.error("RuntimeError during serve()", error=str(e), exc_info=True)
                    with open(debug_log_path, "a") as f:
                        f.write(f"RuntimeError: {str(e)}\n")
                    raise
            logger.info("Plugin server shutting down normally")
            with open(debug_log_path, "a") as f:
                f.write("Plugin server shutting down normally\n")
            sys.exit(0)
        except KeyboardInterrupt:
            logger.info("Plugin server interrupted by user")
            with open(debug_log_path, "a") as f:
                f.write("KeyboardInterrupt\n")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Plugin server failed to start: {e}", exc_info=True)
            with open(debug_log_path, "a") as f:
                import traceback as tb
                f.write(f"Exception: {str(e)}\n")
                f.write(tb.format_exc())
            import traceback
            traceback.print_exc()
            sys.exit(1)

    # Normal CLI invocation
    main_cli(obj={})


if __name__ == "__main__":
    entry_point()


# 🍲🥄🖥️🪄

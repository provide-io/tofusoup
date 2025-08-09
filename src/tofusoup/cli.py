#!/usr/bin/env python3
#
# tofusoup/cli.py
#
import os
import pathlib
import sys

import click
from rich import print as rich_print_direct
from rich.tree import Tree

from pyvider.telemetry import LoggingConfig, TelemetryConfig, logger, setup_telemetry
from tofusoup.common.config import TofuSoupConfigError, load_tofusoup_config
from tofusoup.common.lazy_group import LazyGroup
from tofusoup.common.rich_utils import build_rich_tree_from_dict

LOG_LEVELS = ["NOTSET", "TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

telemetry_config = TelemetryConfig(
    service_name="tofusoup-cli",
    logging=LoggingConfig(
        default_level=os.environ.get("TOFUSOUP_LOG_LEVEL", "INFO").upper()
    ),
)
setup_telemetry(config=telemetry_config)

LAZY_COMMANDS = {
    "sui": ("tofusoup.browser.cli", "sui_cli"),
    "registry": ("tofusoup.registry.cli", "registry_cli"),
    "cty": ("tofusoup.cty.cli", "cty_cli"),
    "hcl": ("tofusoup.hcl.cli", "hcl_cli"),
    "harness": ("tofusoup.harness.cli", "harness_cli"),
    "package": ("tofusoup.package.cli", "package_cli_entry"),
    "provider": ("tofusoup.provider.cli", "provider_cli"),
    "rpc": ("tofusoup.rpc.cli", "rpc_cli"),
    "state": ("tofusoup.state", "state_cli"),
    "stir": ("tofusoup.stir", "stir_cli"),
    "workenv": ("wrkenv.env.cli", "workenv_cli"),
    "we": ("wrkenv.env.cli", "workenv_cli"),  # Alias for workenv
    "test": ("tofusoup.testing.cli", "test_cli"),
    "wire": ("tofusoup.wire.cli", "wire"),
    "garnish": ("tofusoup.garnish.cli", "garnish_cli"),
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
def main_cli(
    ctx: click.Context, verbose: bool, log_level: str | None, config_file: str | None
):
    ctx.obj = ctx.obj or {}

    final_log_level = "DEBUG" if verbose else log_level
    if final_log_level:
        updated_config = TelemetryConfig(
            service_name="tofusoup-cli",
            logging=LoggingConfig(default_level=final_log_level.upper()),
        )
        setup_telemetry(config=updated_config)
        logger.debug(f"Log level set to {final_log_level.upper()} by CLI option.")

    current_path = pathlib.Path(__file__).resolve()
    project_root_path = current_path
    while project_root_path != project_root_path.parent:
        if (project_root_path / "pyproject.toml").exists():
            break
        project_root_path = project_root_path.parent
    else:
        raise FileNotFoundError(
            "Could not determine project root containing 'pyproject.toml'."
        )

    try:
        loaded_config = load_tofusoup_config(
            project_root_path, explicit_config_file=config_file
        )
    except TofuSoupConfigError as e:
        logger.error(f"Configuration Error: {e}. Aborting.")
        sys.exit(1)
    ctx.obj["TOFUSOUP_CONFIG"] = loaded_config

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@click.group("config")
def config_cli():
    """Commands for TofuSoup configuration management."""
    pass


@config_cli.command("show")
@click.pass_context
def show_config_command(ctx: click.Context):
    """Displays the currently loaded TofuSoup configuration."""
    loaded_config = ctx.obj.get("TOFUSOUP_CONFIG", {})
    if not loaded_config:
        rich_print_direct(
            "[yellow]No TofuSoup configuration loaded or configuration is empty.[/yellow]"
        )
        return

    config_tree = Tree("🍲 [bold green]Loaded TofuSoup Configuration[/bold green]")
    build_rich_tree_from_dict(config_tree, loaded_config, "Config Root")
    rich_print_direct(config_tree)


main_cli.add_command(config_cli)


def entry_point():
    main_cli(obj={})


if __name__ == "__main__":
    entry_point()


# 🍲🥄🖥️🪄

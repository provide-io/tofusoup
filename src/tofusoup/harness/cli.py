#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import os
import sys

import click
from provide.foundation import logger
from rich import print as rich_print
from rich.table import Table

from tofusoup.common.exceptions import TofuSoupError
from tofusoup.common.utils import get_cache_dir

from .logic import (
    GO_HARNESS_CONFIG,
    GoVersionError,
    HarnessBuildError,
    ensure_go_harness_build,
)


@click.group("harness")
def harness_cli() -> None:
    """Commands to build, list, and clean test harnesses."""
    pass


@harness_cli.command("clean")
@click.argument("harness_names", nargs=-1)
@click.option("--all", "clean_all", is_flag=True, help="Clean all harnesses.")
@click.pass_context
def clean_harness_command(ctx: click.Context, harness_names: tuple[str, ...], clean_all: bool) -> None:
    """Cleans (removes) specified test harnesses."""
    project_root = ctx.obj["PROJECT_ROOT"]
    harness_bin_dir = get_cache_dir() / "harnesses"

    names_to_clean = []
    if clean_all:
        names_to_clean = list(GO_HARNESS_CONFIG.keys())
    elif harness_names:
        names_to_clean = list(harness_names)
    else:
        rich_print("[yellow]Please specify harness names to clean or use --all.[/yellow]")
        return

    rich_print(f"[bold yellow]Cleaning harnesses: {', '.join(names_to_clean)}[/bold yellow]")
    for name in names_to_clean:
        if name in GO_HARNESS_CONFIG:
            output_name = GO_HARNESS_CONFIG[name]["output_name"]
            harness_path = harness_bin_dir / output_name
            # Try to show path relative to project root, but fall back to absolute path if outside project
            try:
                display_path = harness_path.relative_to(project_root)
            except ValueError:
                display_path = harness_path
            if harness_path.exists():
                try:
                    harness_path.unlink()
                    rich_print(f"[green]Removed harness '{name}': {display_path}[/green]")
                except OSError as e:
                    logger.error(f"Failed to remove harness '{name}': {e}")
                    sys.exit(1)
            else:
                rich_print(f"[yellow]Harness '{name}' not found at {display_path}. Skipping.[/yellow]")
        else:
            logger.warning(f"Unknown harness: '{name}'. Skipping.")


@harness_cli.command("list")
@click.pass_context
def list_harnesses_command(ctx: click.Context) -> None:
    """Lists all available harnesses and their status."""
    project_root = ctx.obj["PROJECT_ROOT"]
    table = Table(title="Go Harnesses")
    table.add_column("Name", style="magenta")
    table.add_column("Output Path", style="yellow")
    table.add_column("Status", style="cyan")
    harness_bin_dir = get_cache_dir() / "harnesses"
    for name, config in GO_HARNESS_CONFIG.items():
        output_path = harness_bin_dir / config["output_name"]
        status = "[red]Not Built[/red]"
        if output_path.exists() and os.access(output_path, os.X_OK):
            status = "[green]Built[/green]"
        # Try to show path relative to project root, but fall back to absolute path if outside project
        try:
            display_path = str(output_path.relative_to(project_root))
        except ValueError:
            display_path = str(output_path)
        table.add_row(name, display_path, status)
    rich_print(table)


@harness_cli.command("build")
@click.argument("harness_names", nargs=-1)
@click.option(
    "--force-rebuild",
    is_flag=True,
    help="Force rebuild even if the harness already exists.",
)
@click.option("--log-level", default="info", help="Set the logging level for the harness build.")
@click.pass_context
def build_harness_command(
    ctx: click.Context, harness_names: tuple[str, ...], force_rebuild: bool, log_level: str
) -> None:
    """Builds specified test harnesses."""
    project_root = ctx.obj["PROJECT_ROOT"]
    loaded_config = ctx.obj.get("TOFUSOUP_CONFIG", {})
    names_to_build = list(harness_names) or list(GO_HARNESS_CONFIG.keys())

    rich_print(f"[bold cyan]Building harness: {', '.join(names_to_build)}[/bold cyan]")
    for name in names_to_build:
        try:
            executable_path = ensure_go_harness_build(name, project_root, loaded_config, force_rebuild)
            # Try to show path relative to project root, but fall back to absolute path if outside project
            try:
                display_path = executable_path.relative_to(project_root)
            except ValueError:
                display_path = executable_path
            rich_print(f"[green]Go harness '{name}' is available at:[/green] {display_path}")
        except (GoVersionError, HarnessBuildError, TofuSoupError) as e:
            logger.error(f"Failed to build Go harness '{name}': {e}")
            sys.exit(1)


# 🥣🔬🔚

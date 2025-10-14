# src/tofusoup/provider/cli.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import click

from tofusoup.scaffolding.generator import scaffold_new_provider


@click.group("provider")
def provider_cli() -> None:
    """Commands for managing provider projects."""
    pass


@provider_cli.command("new")
@click.argument("project_dir", type=click.Path(file_okay=False, writable=True))
def new_provider_command(project_dir: str) -> None:
    """Initialize a new Pyvider provider project."""
    try:
        project_path = scaffold_new_provider(Path(project_dir))
        click.secho(f"✅ New provider project created at {project_path}", fg="green")
    except Exception as e:
        click.secho(f"❌ Project initialization failed: {e}", fg="red", err=True)
        raise click.Abort() from e


# 🍜🍲🏗️🪄

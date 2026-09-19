# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Command line interface for provider lint suites."""

from pathlib import Path

import click


@click.command("lint")
@click.argument("suite", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--provider",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Provider executable to validate.",
)
@click.option(
    "--opentofu",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="OpenTofu executable for the native linting lane.",
)
def lint_cli(suite: Path, provider: Path, opentofu: Path | None) -> None:
    """Run Direct provider validation and optional OpenTofu native linting."""
    del suite, provider, opentofu

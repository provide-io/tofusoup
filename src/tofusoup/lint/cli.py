# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Command line interface for provider lint suites."""

from pathlib import Path

import click

from tofusoup.lint.render import render_json, render_terminal
from tofusoup.lint.runner import LintRunError, run_suite
from tofusoup.lint.suite import SuiteError, load_suite


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
@click.option("--json", "as_json", is_flag=True, help="Emit stable machine-readable results.")
def lint_cli(suite: Path, provider: Path, opentofu: Path | None, as_json: bool) -> None:
    """Run Direct provider validation and optional OpenTofu native linting."""
    try:
        result = run_suite(load_suite(suite), provider, opentofu)
    except (LintRunError, SuiteError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(render_json(result) if as_json else render_terminal(result))

#!/usr/bin/env python3
#
# tofusoup/package/cli.py
#
from pathlib import Path

import click

from flavor.api import (
    build_package_from_manifest,
    clean_cache,
    generate_keys,
    verify_package,
)
from flavor.exceptions import BuildError
from tofusoup.scaffolding.generator import scaffold_new_provider


@click.group("package")
def package_cli_entry():
    """Commands for managing PSPF v0.1 packages and provider projects."""
    pass


@package_cli_entry.command("build")
@click.option(
    "--manifest",
    default="pyproject.toml",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the pyproject.toml manifest file.",
)
def build_command(manifest: str) -> None:
    """Builds a PSPF v0.1 package using the pspf library."""
    click.echo("🚀 Packaging provider...")
    try:
        artifacts = build_package_from_manifest(Path(manifest))
        for artifact in artifacts:
            click.secho(f"✅ Successfully built: {artifact}", fg="green")
    except BuildError as e:
        click.secho(f"❌ Build failed: {e}", fg="red", err=True)
        raise click.Abort()


@package_cli_entry.command("keygen")
@click.option(
    "--out-dir",
    default="keys",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    help="Directory to save the ECDSA key pair.",
)
def keygen_command(out_dir: str) -> None:
    """Generates signing keys using the pspf library."""
    try:
        generate_keys(Path(out_dir))
        click.secho(f"✅ Keys generated in '{out_dir}'", fg="green")
    except BuildError as e:
        click.secho(f"❌ Key generation failed: {e}", fg="red", err=True)
        raise click.Abort()


@package_cli_entry.command("verify")
@click.argument(
    "package_file", type=click.Path(exists=True, dir_okay=False, resolve_path=True)
)
def verify_command(package_file: str) -> None:
    """Verifies a PSPF v0.1 package using the pspf library."""
    click.echo(f"🔍 Verifying '{package_file}'...")
    try:
        verify_package(Path(package_file))
        click.secho("✅ Package verification successful.", fg="green")
    except (BuildError, Exception) as e:
        click.secho(f"❌ Verification failed: {e}", fg="red", err=True)
        raise click.Abort()


@package_cli_entry.command("init")
@click.argument("project_dir", type=click.Path(file_okay=False, writable=True))
def init_command(project_dir: str) -> None:
    """Initializes a new provider project."""
    try:
        path = scaffold_new_provider(Path(project_dir))
        click.secho(f"✅ New project created at {path}", fg="green")
    except Exception as e:
        click.secho(f"❌ Initialization failed: {e}", fg="red", err=True)
        raise click.Abort()


@package_cli_entry.command("clean")
def clean_command() -> None:
    """Removes cached Go binaries using the pspf library."""
    click.echo("🧹 Cleaning cache...")
    clean_cache()
    click.secho("✅ Cache cleaned.", fg="green")


# 🍲🥄🖥️🪄

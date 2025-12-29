#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TofuSoup State Commands

Provides commands for inspecting and manipulating Terraform state,
including decrypting private state data for debugging."""

import base64
import json
from pathlib import Path
from typing import Any

import click
import msgpack
from provide.foundation import logger
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from pyvider.common.encryption import decrypt
from tofusoup.config.defaults import DEFAULT_OUTPUT_FORMAT, DEFAULT_TFSTATE_FILE

console = Console()


def load_terraform_state(state_file: Path) -> dict[str, Any]:
    """Load and parse Terraform state file."""
    try:
        with state_file.open() as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON in state file: {e}") from e
    except FileNotFoundError as e:
        raise click.ClickException(f"State file not found: {state_file}") from e


def find_resources_with_private_state(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Find all resources in state that have private state data."""
    resources_with_private = []

    for resource in state.get("resources", []):
        for instance in resource.get("instances", []):
            private_data = instance.get("private")
            if private_data:
                resources_with_private.append(
                    {
                        "type": resource.get("type"),
                        "name": resource.get("name"),
                        "provider": resource.get("provider"),
                        "mode": resource.get("mode"),
                        "private": private_data,
                        "attributes": instance.get("attributes", {}),
                    }
                )

    return resources_with_private


def decrypt_private_state(encrypted_private: str) -> dict[str, Any] | None:
    """Decrypt private state data using framework encryption."""
    try:
        # Decode base64
        encrypted_bytes = base64.b64decode(encrypted_private)

        # Decrypt using pyvider encryption
        decrypted_bytes = decrypt(encrypted_bytes)

        # Unpack msgpack
        private_data = msgpack.unpackb(decrypted_bytes, raw=False)

        return private_data
    except Exception as e:
        logger.debug(f"Failed to decrypt private state: {e}")
        return None


def display_resource_overview(resources: list[dict[str, Any]]) -> None:
    """Display an overview table of resources with private state."""
    if not resources:
        console.print("[yellow]No resources with private state found.[/yellow]")
        return

    table = Table(title="Resources with Private State")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Mode", style="blue")
    table.add_column("Provider", style="green")
    table.add_column("Private Data", style="yellow")

    for resource in resources:
        private_status = "🔐 encrypted" if resource.get("has_private_data") else "—"
        table.add_row(
            resource["type"],
            resource["name"],
            resource["mode"],
            resource["provider"] or "N/A",
            private_status,
        )

    console.print(table)


def display_resource_details(resource: dict[str, Any], show_encrypted: bool = False) -> None:
    """Display detailed information about a resource including private state."""

    # Resource header
    resource_title = f"{resource['type']}.{resource['name']}"
    console.print(f"\n[bold cyan]{resource_title}[/bold cyan]")

    # Public attributes
    if resource["attributes"]:
        attrs_tree = Tree("📋 [bold]Public Attributes[/bold]")
        for key, value in resource["attributes"].items():
            # Format value for display
            if isinstance(value, dict | list):
                json.dumps(value, indent=2)
                attrs_tree.add(f"[green]{key}[/green]: [dim]{type(value).__name__}[/dim]")
            else:
                attrs_tree.add(f"[green]{key}[/green]: [white]{value}[/white]")
        console.print(attrs_tree)

    # Private state
    if resource["private"]:
        console.print("\n[bold yellow]🔐 Private State[/bold yellow]")

        if show_encrypted:
            console.print("[dim]Encrypted (Base64):[/dim]")
            encrypted_panel = Panel(
                resource["private"],
                title="Encrypted Private State",
                border_style="yellow",
            )
            console.print(encrypted_panel)

        # Try to decrypt
        decrypted = decrypt_private_state(resource["private"])
        if decrypted:
            console.print("[dim]Decrypted Content:[/dim]")
            decrypted_json = json.dumps(decrypted, indent=2, default=str)
            syntax = Syntax(decrypted_json, "json", theme="monokai", line_numbers=True)
            console.print(syntax)
        else:
            console.print("[red]❌ Failed to decrypt private state[/red]")
            console.print("[dim]This could be due to:[/dim]")
            console.print("[dim]• Missing PYVIDER_PRIVATE_STATE_SHARED_SECRET environment variable[/dim]")
            console.print("[dim]• Incorrect shared secret[/dim]")
            console.print("[dim]• Corrupted private state data[/dim]")
    else:
        console.print("[dim]No private state data[/dim]")


@click.group("state")
def state_cli() -> None:
    """Commands for inspecting Terraform state with private state support."""


def _get_target_resources(state: dict[str, Any], private_only: bool) -> list[dict[str, Any]]:
    resources_with_private = find_resources_with_private_state(state)
    if private_only:
        return resources_with_private

    target_resources = []
    for res in state.get("resources", []):
        for instance in res.get("instances", []):
            target_resources.append(
                {
                    "type": res.get("type"),
                    "name": res.get("name"),
                    "provider": res.get("provider"),
                    "mode": res.get("mode"),
                    "private": instance.get("private"),
                    "attributes": instance.get("attributes", {}),
                }
            )
    return target_resources


def _display_state_overview(target_resources: list, resources_with_private: list, private_only: bool) -> None:
    if private_only:
        console.print(f"[bold]Found {len(resources_with_private)} resources with private state:[/bold]\n")
    else:
        console.print(
            f"[bold]Found {len(target_resources)} total resources ({len(resources_with_private)} with private state):[/bold]\n"
        )

    display_resource_overview(target_resources if not private_only else resources_with_private)

    if resources_with_private:
        console.print(
            "\n[dim]💡 Use [bold]--resource <type.name>[/bold] to see decrypted private state details[/dim]"
        )
        console.print(
            "[dim]💡 Use [bold]--private-only[/bold] to show only resources with private state[/dim]"
        )


@state_cli.command("show")
@click.argument(
    "state_file",
    type=click.Path(exists=True, dir_okay=False),
    default=DEFAULT_TFSTATE_FILE,
)
@click.option("--resource", "-r", help="Show details for a specific resource (format: type.name)")
@click.option("--show-encrypted", is_flag=True, help="Also show encrypted private state data")
@click.option("--private-only", is_flag=True, help="Only show resources that have private state")
def show_state(state_file: str, resource: str | None, show_encrypted: bool, private_only: bool) -> None:
    """
    Display Terraform state with decrypted private state data.

    This command reads a Terraform state file and displays both public attributes
    and decrypted private state data for resources. Requires the
    PYVIDER_PRIVATE_STATE_SHARED_SECRET environment variable to be set.

    Examples:
        soup state show                              # Show overview of all resources
        soup state show --private-only              # Show only resources with private state
        soup state show -r pyvider_timed_token.example  # Show details for specific resource
        soup state show --show-encrypted            # Include encrypted private state in output
    """
    state_path = Path(state_file)

    try:
        state = load_terraform_state(state_path)
    except click.ClickException:
        raise

    target_resources = _get_target_resources(state, private_only)

    console.print("[bold blue]🗂️  Terraform State Analysis[/bold blue]")
    console.print(f"[dim]State file: {state_path}[/dim]")
    console.print(f"[dim]Terraform version: {state.get('terraform_version', 'unknown')}[/dim]")
    console.print(f"[dim]Serial: {state.get('serial', 'unknown')}[/dim]\n")

    if resource:
        resource_type, resource_name = resource.split(".", 1) if "." in resource else (resource, "")
        found_resource = next(
            (
                res
                for res in target_resources
                if res["type"] == resource_type and (not resource_name or res["name"] == resource_name)
            ),
            None,
        )

        if found_resource:
            display_resource_details(found_resource, show_encrypted)
        else:
            console.print(f"[red]Resource '{resource}' not found in state[/red]")
            return
    else:
        resources_with_private = find_resources_with_private_state(state)
        _display_state_overview(target_resources, resources_with_private, private_only)


@state_cli.command("decrypt")
@click.argument("encrypted_data", type=str)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "raw"]),
    default=DEFAULT_OUTPUT_FORMAT,
    help="Output format",
)
def decrypt_private_data(encrypted_data: str, format: str) -> None:
    """
    Decrypt a base64-encoded private state string.

    This is useful for debugging private state issues or examining private state
    data outside of the full state file context.

    Example:
        soup state decrypt "PaDuMfrlCnnhZsKb..."
    """
    decrypted = decrypt_private_state(encrypted_data)

    if decrypted:
        if format == "json":
            output = json.dumps(decrypted, indent=2, default=str)
            syntax = Syntax(output, "json", theme="monokai", line_numbers=True)
            console.print(syntax)
        else:
            console.print(decrypted)
    else:
        console.print("[red]❌ Failed to decrypt data[/red]")
        console.print("[dim]Ensure PYVIDER_PRIVATE_STATE_SHARED_SECRET is set correctly[/dim]")


@state_cli.command("validate")
@click.argument(
    "state_file",
    type=click.Path(exists=True, dir_okay=False),
    default=DEFAULT_TFSTATE_FILE,
)
def validate_private_state(state_file: str) -> None:
    """
    Validate that all private state in the state file can be decrypted.

    This command checks every resource with private state to ensure the
    private state data can be successfully decrypted with the current
    shared secret.
    """
    state_path = Path(state_file)
    state = load_terraform_state(state_path)
    resources_with_private = find_resources_with_private_state(state)

    if not resources_with_private:
        return

    console.print(f"[bold]Validating private state for {len(resources_with_private)} resources...[/bold]\n")

    valid_count = 0
    invalid_count = 0

    table = Table()
    table.add_column("Resource", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for resource in resources_with_private:
        resource_name = f"{resource['type']}.{resource['name']}"

        decrypted = decrypt_private_state(resource["private"])
        if decrypted:
            valid_count += 1
            table.add_row(
                resource_name,
                f"Decrypted {len(decrypted)} fields",
            )
        else:
            invalid_count += 1
            table.add_row(resource_name, "[red]❌ Invalid[/red]", "Failed to decrypt")

    console.print(table)
    console.print(f"\n[bold]Summary:[/bold] {valid_count} valid, {invalid_count} invalid")

    if invalid_count > 0:
        console.print("\n[red]❌ Some private state data could not be decrypted[/red]")
        console.print("[dim]Check that PYVIDER_PRIVATE_STATE_SHARED_SECRET is correct[/dim]")
        raise click.Abort()
    else:
        console.print("[green]✅ All private state data decrypted successfully[/green]")


if __name__ == "__main__":
    state_cli()

# 🥣🔬🔚

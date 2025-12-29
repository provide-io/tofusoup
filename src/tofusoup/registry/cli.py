#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Commands for querying and managing Terraform/OpenTofu registries."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import click
from provide.foundation import logger

from tofusoup.config.defaults import DEFAULT_REGISTRY_SOURCE, TERRAFORM_REGISTRY_URL
from tofusoup.registry.base import RegistryConfig
from tofusoup.registry.opentofu import OpenTofuRegistry
from tofusoup.registry.search.engine import (
    async_search_runner,
)
from tofusoup.registry.terraform import IBMTerraformRegistry

T = TypeVar("T")


def safe_async_run(coro_func: Callable[[], Awaitable[T]]) -> T:
    """
    Safely run async function, handling both testing and production contexts.

    Uses asyncio.run() directly to avoid event loop conflicts in testing.
    """
    return asyncio.run(coro_func())


@click.group("registry")
@click.pass_context
def registry_cli(ctx: click.Context) -> None:
    """Commands for querying and managing Terraform/OpenTofu registries."""
    logger.debug("TofuSoup 'registry' command group invoked.")


# Provider subcommands
@registry_cli.group("provider")
def provider_group() -> None:
    """Commands for working with providers."""


@provider_group.command("info")
@click.argument("provider", metavar="NAMESPACE/NAME")
@click.option(
    "-r",
    "--registry",
    type=click.Choice(["terraform", "opentofu", "both"], case_sensitive=False),
    default=DEFAULT_REGISTRY_SOURCE,
    help="Registry to query.",
)
@click.pass_context
def provider_info(ctx: click.Context, provider: str, registry: str) -> None:
    """Get detailed information about a provider."""
    try:
        namespace, name = provider.split("/")
    except ValueError:
        click.echo("Error: Provider must be in format 'namespace/name'", err=True)
        return

    async def fetch_info() -> None:
        registries = []
        if registry in ["terraform", "both"]:
            registries.append(IBMTerraformRegistry(RegistryConfig(base_url=TERRAFORM_REGISTRY_URL)))
        if registry in ["opentofu", "both"]:
            registries.append(OpenTofuRegistry())

        for reg in registries:
            async with reg:
                reg_name = reg.__class__.__name__.replace("Registry", "")
                try:
                    provider_data = await reg.get_provider_details(namespace, name)
                    click.echo(f"\n=== {reg_name} Registry ===")
                    click.echo(f"Provider: {namespace}/{name}")
                    click.echo(f"Description: {provider_data.get('description', 'N/A')}")
                    click.echo(f"Source: {provider_data.get('source', 'N/A')}")
                    click.echo(f"Downloads: {provider_data.get('download_count', 'N/A')}")
                except Exception as e:
                    click.echo(f"\n=== {reg_name} Registry ===")
                    click.echo(f"Error: {e}")

    safe_async_run(fetch_info)


@provider_group.command("versions")
@click.argument("provider", metavar="NAMESPACE/NAME")
@click.option(
    "-r",
    "--registry",
    type=click.Choice(["terraform", "opentofu", "both"], case_sensitive=False),
    default=DEFAULT_REGISTRY_SOURCE,
    help="Registry to query.",
)
@click.option("--latest", is_flag=True, help="Show only the latest version.")
@click.pass_context
def provider_versions(ctx: click.Context, provider: str, registry: str, latest: bool) -> None:
    """List all versions of a provider."""
    try:
        namespace, name = provider.split("/")
    except ValueError:
        click.echo("Error: Provider must be in format 'namespace/name'", err=True)
        return

    async def fetch_versions() -> None:
        registries = []
        if registry in ["terraform", "both"]:
            registries.append(IBMTerraformRegistry(RegistryConfig(base_url=TERRAFORM_REGISTRY_URL)))
        if registry in ["opentofu", "both"]:
            registries.append(OpenTofuRegistry())

        for reg in registries:
            async with reg:
                reg_name = reg.__class__.__name__.replace("Registry", "")
                try:
                    await reg.get_provider_details(namespace, name)
                    versions = await reg.list_provider_versions(f"{namespace}/{name}")

                    click.echo(f"\n=== {reg_name} Registry ===")
                    click.echo(f"Provider: {namespace}/{name}")

                    if latest and versions:
                        click.echo(f"Latest version: {versions[0].version}")
                    else:
                        click.echo(f"Versions ({len(versions)} total):")
                        for v in versions[:10]:  # Show first 10
                            platforms = f" ({len(v.platforms)} platforms)" if v.platforms else ""
                            click.echo(f"  - {v.version}{platforms}")
                        if len(versions) > 10:
                            click.echo(f"  ... and {len(versions) - 10} more")
                except Exception as e:
                    click.echo(f"\n=== {reg_name} Registry ===")
                    click.echo(f"Error: {e}")

    safe_async_run(fetch_versions)


# Module subcommands
@registry_cli.group("module")
def module_group() -> None:
    """Commands for working with modules."""


@module_group.command("info")
@click.argument("module", metavar="NAMESPACE/NAME/PROVIDER")
@click.option(
    "-r",
    "--registry",
    type=click.Choice(["terraform", "opentofu", "both"], case_sensitive=False),
    default=DEFAULT_REGISTRY_SOURCE,
    help="Registry to query.",
)
@click.pass_context
def module_info(ctx: click.Context, module: str, registry: str) -> None:
    """Get detailed information about a module."""
    parts = module.split("/")
    if len(parts) != 3:
        click.echo("Error: Module must be in format 'namespace/name/provider'", err=True)
        return

    namespace, name, provider_name = parts

    async def fetch_info() -> None:
        registries = []
        if registry in ["terraform", "both"]:
            registries.append(IBMTerraformRegistry(RegistryConfig(base_url=TERRAFORM_REGISTRY_URL)))
        if registry in ["opentofu", "both"]:
            registries.append(OpenTofuRegistry())

        for reg in registries:
            async with reg:
                reg_name = reg.__class__.__name__.replace("Registry", "")
                try:
                    module_data = await reg.get_module_details(namespace, name, provider_name, "latest")
                    click.echo(f"\n=== {reg_name} Registry ===")
                    click.echo(f"Module: {namespace}/{name}/{provider_name}")
                    click.echo(f"Description: {module_data.get('description', 'N/A')}")
                    click.echo(f"Source: {module_data.get('source', 'N/A')}")
                    click.echo(f"Downloads: {module_data.get('download_count', 'N/A')}")
                except Exception as e:
                    click.echo(f"\n=== {reg_name} Registry ===")
                    click.echo(f"Error: {e}")

    safe_async_run(fetch_info)


@module_group.command("versions")
@click.argument("module", metavar="NAMESPACE/NAME/PROVIDER")
@click.option(
    "-r",
    "--registry",
    type=click.Choice(["terraform", "opentofu", "both"], case_sensitive=False),
    default=DEFAULT_REGISTRY_SOURCE,
    help="Registry to query.",
)
@click.option("--latest", is_flag=True, help="Show only the latest version.")
@click.pass_context
def module_versions(ctx: click.Context, module: str, registry: str, latest: bool) -> None:
    """List all versions of a module."""
    parts = module.split("/")
    if len(parts) != 3:
        click.echo("Error: Module must be in format 'namespace/name/provider'", err=True)
        return

    namespace, name, provider_name = parts

    async def fetch_versions() -> None:
        registries = []
        if registry in ["terraform", "both"]:
            registries.append(IBMTerraformRegistry(RegistryConfig(base_url=TERRAFORM_REGISTRY_URL)))
        if registry in ["opentofu", "both"]:
            registries.append(OpenTofuRegistry())

        for reg in registries:
            async with reg:
                reg_name = reg.__class__.__name__.replace("Registry", "")
                try:
                    await reg.get_module_details(namespace, name, provider_name, "latest")
                    versions = await reg.list_module_versions(f"{namespace}/{name}/{provider_name}")

                    click.echo(f"\n=== {reg_name} Registry ===")
                    click.echo(f"Module: {namespace}/{name}/{provider_name}")

                    if latest and versions:
                        click.echo(f"Latest version: {versions[0].version}")
                    else:
                        click.echo(f"Versions ({len(versions)} total):")
                        for v in versions[:10]:  # Show first 10
                            published = f" (published: {v.published_at})" if v.published_at else ""
                            click.echo(f"  - {v.version}{published}")
                        if len(versions) > 10:
                            click.echo(f"  ... and {len(versions) - 10} more")
                except Exception as e:
                    click.echo(f"\n=== {reg_name} Registry ===")
                    click.echo(f"Error: {e}")

    safe_async_run(fetch_versions)


# Search command (moved from sui)
@registry_cli.command("search")
@click.argument("term", nargs=-1)
@click.option(
    "-r",
    "--registry",
    "registry_name",
    type=click.Choice(["terraform", "opentofu", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Registry to search.",
)
@click.option(
    "-t",
    "--type",
    "resource_type",
    type=click.Choice(["provider", "module", "all"], case_sensitive=False),
    default="all",
    help="Type of resource to search.",
)
def search_command(term: tuple[str, ...], registry_name: str, resource_type: str) -> None:
    """Search registries for providers and modules."""
    search_term = " ".join(term)
    if not search_term:
        click.echo("Please provide a search term.", err=True)
        return

    logger.info(f"Initiating registry search for term: '{search_term}' on registry: '{registry_name}'")

    try:
        results = safe_async_run(lambda: async_search_runner(search_term, registry_name))

        # Filter by type if specified
        if resource_type != "all":
            results = [r for r in results if r.type == resource_type]

        if results:
            click.echo(f"Found {len(results)} results for '{search_term}':")

            # Sort results
            results.sort(
                key=lambda r: (
                    r.registry_source == "both",
                    r.total_versions is not None,
                    r.total_versions,
                ),
                reverse=True,
            )

            # Format output
            max_name_len = (
                max(
                    len(f"{r.namespace}/{r.name}/{r.provider_name}")
                    if r.type == "module"
                    else len(f"{r.namespace}/{r.name}")
                    for r in results
                )
                if results
                else 10
            )
            has_versions = any(r.total_versions is not None for r in results)

            if has_versions:
                max_latest_len = max(len(r.latest_version or "N/A") for r in results) if results else 10
                header = f"| R | T | {'Name':<{max_name_len}} | {'Latest':<{max_latest_len}} | {'Total':<5} | Description"
            else:
                header = f"| R | T | {'Name':<{max_name_len}} | Description"

            click.echo(header)
            click.echo("-" * len(header))

            for result in results:
                desc = result.description or "N/A"
                if len(desc) > 70:
                    desc = desc[:67] + "..."

                registry_emoji = (
                    "🤝"
                    if result.registry_source == "both"
                    else "🍲"
                    if result.registry_source == "opentofu"
                    else "🏢"
                )
                type_emoji = "📦" if result.type == "module" else "🔌"
                name = (
                    f"{result.namespace}/{result.name}/{result.provider_name}"
                    if result.type == "module"
                    else f"{result.namespace}/{result.name}"
                )

                if has_versions:
                    latest = result.latest_version or "N/A"
                    total = str(result.total_versions) if result.total_versions is not None else "N/A"
                    click.echo(
                        f"| {registry_emoji} | {type_emoji} | {name:<{max_name_len}} | {latest:<{max_latest_len}} | {total:<5} | {desc}"
                    )
                else:
                    click.echo(f"| {registry_emoji} | {type_emoji} | {name:<{max_name_len}} | {desc}")

        else:
            click.echo(f"No results found for '{search_term}' on {registry_name} registry.")

    except Exception as e:
        logger.error(f"Error in search_command: {e}", exc_info=True)
        click.echo(f"A critical error occurred: {e}", err=True)


async def _fetch_tf_data(
    resource_type: str, namespace: str, name: str, provider_name: str | None
) -> tuple[dict | None, list, str, int]:
    tf_registry = IBMTerraformRegistry(RegistryConfig(base_url="https://registry.terraform.io"))
    async with tf_registry:
        try:
            if resource_type == "provider":
                tf_data = await tf_registry.get_provider_details(namespace, name)
                tf_versions = await tf_registry.list_provider_versions(f"{namespace}/{name}")
            else:
                tf_data = await tf_registry.get_module_details(namespace, name, provider_name, "latest")
                tf_versions = await tf_registry.list_module_versions(f"{namespace}/{name}/{provider_name}")
            tf_latest = tf_versions[0].version if tf_versions else "N/A"
            tf_count = len(tf_versions)
            return tf_data, tf_versions, tf_latest, tf_count
        except Exception:
            return None, [], "Not found", 0


async def _fetch_tofu_data(
    resource_type: str, namespace: str, name: str, provider_name: str | None
) -> tuple[dict | None, list, str, int]:
    tofu_registry = OpenTofuRegistry()
    async with tofu_registry:
        try:
            if resource_type == "provider":
                tofu_data = await tofu_registry.get_provider_details(namespace, name)
                tofu_versions = await tofu_registry.list_provider_versions(f"{namespace}/{name}")
            else:
                tofu_data = await tofu_registry.get_module_details(namespace, name, provider_name, "latest")
                tofu_versions = await tofu_registry.list_module_versions(f"{namespace}/{name}/{provider_name}")
            tofu_latest = tofu_versions[0].version if tofu_versions else "N/A"
            tofu_count = len(tofu_versions)
            return tofu_data, tofu_versions, tofu_latest, tofu_count
        except Exception:
            return None, [], "Not found", 0


def _display_comparison(
    tf_data: Any,
    tf_latest: str,
    tf_count: int,
    tofu_data: Any,
    tofu_latest: str,
    tofu_count: int,
    tf_versions: list[Any],
    tofu_versions: list[Any],
) -> None:
    click.echo(f"\n{'Registry':<20} | {'Status':<12} | {'Latest':<10} | {'Versions':<8}")
    click.echo("-" * 60)

    tf_status = "Available" if tf_data else "Not found"
    click.echo(f"{'Terraform Registry':<20} | {tf_status:<12} | {tf_latest:<10} | {tf_count:<8}")

    tofu_status = "Available" if tofu_data else "Not found"
    click.echo(f"{'OpenTofu Registry':<20} | {tofu_status:<12} | {tofu_latest:<10} | {tofu_count:<8}")

    if tf_data and tofu_data and tf_versions and tofu_versions:
        click.echo("\nVersion Availability:")
        all_versions = sorted(
            set([v.version for v in tf_versions] + [v.version for v in tofu_versions]),
            reverse=True,
        )

        for version in all_versions[:10]:
            tf_has = "✓" if any(v.version == version for v in tf_versions) else "✗"
            tofu_has = "✓" if any(v.version == version for v in tofu_versions) else "✗"
            click.echo(f"  {version:<15} TF: {tf_has}  OpenTofu: {tofu_has}")

        if len(all_versions) > 10:
            click.echo(f"  ... and {len(all_versions) - 10} more versions")


# Compare command
@registry_cli.command("compare")
@click.argument("resource", metavar="NAMESPACE/NAME[/PROVIDER]")
def compare_command(resource: str) -> None:
    """Compare a resource across Terraform and OpenTofu registries."""
    parts = resource.split("/")

    if len(parts) == 2:
        namespace, name = parts
        provider_name = None
        resource_type = "provider"
    elif len(parts) == 3:
        namespace, name, provider_name = parts
        resource_type = "module"
    else:
        click.echo(
            "Error: Resource must be 'namespace/name' for providers or 'namespace/name/provider' for modules",
            err=True,
        )
        return

    async def compare_resources() -> None:
        click.echo(f"\nComparing {resource_type}: {resource}")
        click.echo("=" * 60)

        tf_data, tf_versions, tf_latest, tf_count = await _fetch_tf_data(
            resource_type, namespace, name, provider_name
        )
        tofu_data, tofu_versions, tofu_latest, tofu_count = await _fetch_tofu_data(
            resource_type, namespace, name, provider_name
        )

        _display_comparison(
            tf_data, tf_latest, tf_count, tofu_data, tofu_latest, tofu_count, tf_versions, tofu_versions
        )

    safe_async_run(compare_resources)


# 🥣🔬🔚

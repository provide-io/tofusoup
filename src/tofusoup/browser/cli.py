#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import click
from provide.foundation import get_hub, logger

from tofusoup.browser.ui.app import TFBrowserApp


@click.group("sui")
@click.pass_context
def sui_cli(ctx: click.Context) -> None:
    """Graphical UI for browsing Terraform and OpenTofu registries."""
    logger.debug("TofuSoup 'sui' command group invoked.")
    pass


@sui_cli.command("tui")
@click.option(
    "-r",
    "--registry",
    "registry_name",
    type=str,
    help="Name of the registry to pre-select or focus in TUI (e.g., 'terraform', 'opentofu').",
)
@click.pass_context
def tui_command(ctx: click.Context, registry_name: str | None) -> None:
    """Launch the Textual TUI to browse registries."""
    logger.info(f"Launching TUI browser. Specified registry context: {registry_name or 'not specified'}")
    app = TFBrowserApp()
    try:
        app.run()
    except Exception as e:
        # This block will now correctly log to stderr because of the finally block.
        logger.error(f"Error running TUI browser: {e}", exc_info=True)
        click.echo(f"Failed to launch TUI: {e}", err=True)
    finally:
        # FIX: Reset the logger to its default state (writing to stderr).
        # This is critical to prevent logging calls after the TUI has exited
        # from trying to write to a destroyed widget, which causes the NoActiveAppError.
        hub = get_hub()
        hub.initialize_foundation()  # Re-initialize to default stderr logging
        logger.info("TUI browser exited.")


# 🥣🔬🔚

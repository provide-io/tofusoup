# type: ignore
#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""CLI commands for HCL operations."""

import pathlib
import sys

import click
from provide.foundation import logger  # Changed import
from rich import print as rich_print
from rich.tree import Tree

from tofusoup.common.exceptions import ConversionError, TofuSoupError

# from tofusoup.common.rich_utils import build_rich_tree_from_cty_json_comparable # Moved to common
from tofusoup.common.rich_utils import build_rich_tree_from_cty_json_comparable
from tofusoup.cty.logic import cty_value_to_json_comparable_dict  # For view command

from .logic import convert_hcl_file_to_output_format, load_hcl_file_as_cty

# logger = telemetry.get_logger(__name__) # Removed old way


@click.group("hcl")
def hcl_cli() -> None:
    """Commands for HCL (HashiCorp Configuration Language) operations."""


@hcl_cli.command("view")
@click.argument("filepath", type=click.Path(exists=True, dir_okay=False, readable=True))
@click.pass_context
def view_command(ctx: click.Context, filepath: str) -> None:
    """Parses an HCL file and displays its structure as a CTY representation."""
    verbose = ctx.obj.get("VERBOSE", False)
    input_file_path = pathlib.Path(filepath)

    try:
        cty_value = load_hcl_file_as_cty(filepath)
        # Convert the CtyValue to the JSON-comparable dictionary structure for tree building
        comparable_dict = cty_value_to_json_comparable_dict(cty_value)

        tree_title = (
            f":page_facing_up: [bold blue]{input_file_path.name}[/bold blue] ([italic]HCL as CTY[/italic])"
        )
        rich_tree = Tree(tree_title)
        build_rich_tree_from_cty_json_comparable(rich_tree, comparable_dict, "HCL Root (as CTY)")
        rich_print(rich_tree)

    except ConversionError as e:  # Catch specific conversion errors from logic.py
        logger.error(
            f"Error processing HCL file: {e}", exc_info=verbose
        )  # exc_info=False if e.message is good
        sys.exit(1)
    except TofuSoupError as e:
        logger.error(f"Error: {e}", exc_info=verbose)
        sys.exit(1)
    except Exception as e:  # Catch-all for other unexpected issues
        logger.error(
            f"An unexpected error occurred while viewing HCL file: {e}",
            exc_info=verbose,
        )
        sys.exit(1)


@hcl_cli.command("convert")
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, readable=True))
@click.argument("output_file", type=click.Path(dir_okay=False, writable=True, allow_dash=True))
@click.option(
    "--output-format",
    "-of",
    "output_format_opt",
    type=click.Choice(["json", "msgpack"], case_sensitive=False),
    default=None,
    help='Format for the output. Inferred if not provided. Default can be set in soup.toml via command_options."hcl.convert".default_output_format.',
)
@click.pass_context
def convert_command(
    ctx: click.Context, input_file: str, output_file: str, output_format_opt: str | None
) -> None:
    """
    Converts an HCL file to JSON or Msgpack (via CTY representation).

    INPUT_FILE must be an HCL file.
    OUTPUT_FILE can be a file path or '-' for stdout.

    Examples:
      soup hcl convert my_config.tfvars output.json
      soup hcl convert deployment.hcl deployment.mpk
      soup hcl convert variables.tf - --output-format json # Output JSON to stdout
    """
    verbose = ctx.obj.get("VERBOSE", False)
    loaded_config = ctx.obj.get("TOFUSOUP_CONFIG", {})
    cmd_opts = loaded_config.get("command_options", {}).get("hcl.convert", {})

    actual_output_format = _determine_output_format(output_format_opt, cmd_opts, output_file)

    if verbose:  # Log final decision
        logger.info(
            f"Output: {output_file}, Using format: {actual_output_format} "
            f"(CLI option: {output_format_opt}, Config: {cmd_opts.get('default_output_format')})"
        )

    try:
        content_or_none = convert_hcl_file_to_output_format(
            input_filepath_str=input_file,
            output_filepath_str=output_file,
            output_format=actual_output_format,  # type: ignore
            output_to_stdout=(output_file == "-"),
        )

        if output_file == "-":
            _handle_stdout_output(content_or_none)
        else:
            rich_print(
                f"[green]HCL file '{input_file}' converted to {actual_output_format.upper()} "
                f"and saved to '{output_file}'[/green]"
            )

    except ConversionError as e:
        logger.error(f"HCL conversion failed: {e}", exc_info=verbose)
        sys.exit(1)
    except TofuSoupError as e:
        logger.error(f"Error: {e}", exc_info=verbose)
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during HCL conversion: {e}", exc_info=verbose)
        sys.exit(1)


def _determine_output_format(output_format_opt: str | None, cmd_opts: dict, output_file: str) -> str:
    """Determine the output format from CLI, config, or file extension inference."""
    # CLI option takes precedence
    if output_format_opt:
        return output_format_opt

    # Try configuration default
    config_format = cmd_opts.get("default_output_format")
    if config_format:
        logger.debug(f"Using default output format '{config_format}' from soup.toml for hcl.convert")
        return config_format

    # Try inference from output file
    return _infer_output_format(output_file)


def _infer_output_format(output_file: str) -> str:
    """Infer output format from file extension."""
    if output_file == "-":
        logger.error(
            "Cannot infer output format when writing to stdout ('-'). "
            "Specify --output-format or set default_output_format in soup.toml for hcl.convert."
        )
        sys.exit(1)

    output_file_path_obj = pathlib.Path(output_file)
    ext_out = output_file_path_obj.suffix.lower()

    if ext_out == ".json":
        format_name = "json"
    elif ext_out in [".mpk", ".msgpack"]:
        format_name = "msgpack"
    else:
        logger.error(
            f"Could not infer output format for '{output_file}' from extension '{ext_out}'. "
            f"Supported: .json, .mpk, .msgpack. Specify --output-format or "
            f"set default_output_format in soup.toml for hcl.convert."
        )
        sys.exit(1)

    logger.debug(f"Inferred output format for HCL conversion as: {format_name}")
    return format_name


def _handle_stdout_output(content_or_none: str | bytes | None) -> None:
    """Handle output to stdout."""
    if isinstance(content_or_none, str):
        click.echo(content_or_none, nl=False)
        if not content_or_none.endswith("\n"):
            sys.stdout.write("\n")
    elif isinstance(content_or_none, bytes):
        if sys.stdout.isatty():
            rich_print(
                "[yellow]Warning:[/yellow] Msgpack output to TTY is binary. "
                "Consider saving to a file or piping."
            )
        sys.stdout.buffer.write(content_or_none)
        sys.stdout.buffer.flush()


# 🥣🔬🔚

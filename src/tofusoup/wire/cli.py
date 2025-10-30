#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import json
from pathlib import Path

import click
import msgpack
from rich import print_json

from .logic import convert_json_to_msgpack, convert_msgpack_to_json


@click.group()
def wire() -> None:
    """Commands for working with the Terraform wire protocol."""
    pass


@wire.command("to-msgpack")
@click.argument(
    "input_path",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True, path_type=Path),
)
@click.option(
    "-o",
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    help="Output file path. Defaults to the input file with a .msgpack extension.",
)
def to_msgpack(input_path: Path, output_path: Path | None) -> None:
    """Converts a JSON file to the MessagePack wire format."""
    try:
        convert_json_to_msgpack(input_path, output_path)
    except (json.JSONDecodeError, msgpack.exceptions.PackException) as e:
        raise click.ClickException(f"Error during conversion: {e}") from e
    except Exception as e:
        raise click.ClickException(f"An unexpected error occurred: {e}") from e


@wire.command("to-json")
@click.argument(
    "input_path",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True, path_type=Path),
)
@click.option(
    "-o",
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    help="Output file path. Defaults to the input file with a .json extension.",
)
@click.option(
    "--pretty/--no-pretty",
    default=True,
    help="Pretty-print the JSON output to the console.",
)
def to_json(input_path: Path, output_path: Path | None, pretty: bool) -> None:
    """Converts a MessagePack wire format file to JSON."""
    try:
        result_path = convert_msgpack_to_json(input_path, output_path)
        if pretty:
            # Read back the result for pretty printing
            json_data = result_path.read_text("utf-8")
            print_json(json_data)
    except msgpack.exceptions.UnpackException as e:
        raise click.ClickException(f"Error unpacking MessagePack file: {e}") from e
    except Exception as e:
        raise click.ClickException(f"An unexpected error occurred: {e}") from e


# 🥣🔬🔚

# type: ignore
#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import json
from pathlib import Path
import sys
from typing import TextIO

import click

from pyvider.cty import (
    CtyDynamic,
    parse_tf_type_to_ctytype,
)
from pyvider.cty.codec import cty_from_msgpack, cty_to_msgpack
from pyvider.cty.conversion import encode_cty_type_to_wire_json

from ..common.rich_utils import print_json


@click.group("cty")
def cty_cli() -> None:
    """Commands for working with cty values."""


@cty_cli.command("view")
@click.argument("input_file", type=click.File("rb"))
@click.option(
    "--input-format",
    type=click.Choice(["json", "msgpack"]),
    default="json",
    help="Format of the input file.",
)
@click.option("--type", "type_spec", help="CTY type specification (JSON format).")
def view_command(input_file: TextIO, input_format: str, type_spec: str) -> None:
    """View CTY data in a human-readable format."""
    try:
        data = input_file.read()

        if type_spec:
            # Parse the type specification - Go expects JSON format
            # So we need to parse it the same way: as JSON bytes
            type_data = json.loads(type_spec) if type_spec.startswith('"') else type_spec
            cty_type = parse_tf_type_to_ctytype(type_data)
        # Try to infer type from JSON structure
        elif input_format == "json":
            json_data = json.loads(data.decode())
            # For now, use dynamic type - could be improved with type inference
            cty_type = CtyDynamic()
        else:
            click.echo("--type is required for MessagePack input", err=True)
            sys.exit(1)

        # Deserialize the value
        if input_format == "json":
            # For JSON, we need to parse and validate the JSON as a CTY value
            json_data = json.loads(data.decode())
            cty_value = cty_type.validate(json_data)
        else:  # msgpack
            cty_value = cty_from_msgpack(data, cty_type)

        # Display the value in a readable format
        output = {
            "type": encode_cty_type_to_wire_json(cty_value.type),
            "value": cty_value.value if not cty_value.is_unknown else "<unknown>",
            "is_null": cty_value.is_null,
            "is_unknown": cty_value.is_unknown,
            "marks": list(str(mark) for mark in cty_value.marks) if cty_value.marks else [],
        }

        print_json(output)

    except Exception as e:
        click.echo(f"Error viewing CTY data: {e}", err=True)
        sys.exit(1)


@cty_cli.command("convert")
@click.argument("input_file", type=click.File("rb"))
@click.argument("output_file", type=click.Path())
@click.option(
    "--input-format",
    type=click.Choice(["json", "msgpack"]),
    default="json",
    help="Format of the input file.",
)
@click.option(
    "--output-format",
    type=click.Choice(["json", "msgpack"]),
    default="json",
    help="Format for the output file.",
)
@click.option("--type", "type_spec", required=True, help="CTY type specification (JSON format).")
def convert_command(
    input_file: TextIO,
    output_file: str,
    input_format: str,
    output_format: str,
    type_spec: str,
) -> None:
    """Convert CTY data between JSON and MessagePack formats."""
    try:
        # Parse input data
        data = input_file.read()
        # Parse type spec the same way Go does - as JSON bytes
        type_data = json.loads(type_spec) if type_spec.startswith('"') else type_spec
        cty_type = parse_tf_type_to_ctytype(type_data)

        # Deserialize based on input format
        if input_format == "json":
            json_data = json.loads(data.decode())
            cty_value = cty_type.validate(json_data)
        else:  # msgpack
            cty_value = cty_from_msgpack(data, cty_type)

        # Serialize to output format
        if output_format == "json":
            output_data = json.dumps(cty_value.value, indent=2)
            mode = "w"
        else:  # msgpack
            output_data = cty_to_msgpack(cty_value, cty_type)
            mode = "wb"

        # Write output file
        output_path = Path(output_file)
        if mode == "w":
            output_path.write_text(output_data)
        else:
            output_path.write_bytes(output_data)

        click.echo(f"Converted {input_format} to {output_format}: {output_file}")

    except Exception as e:
        click.echo(f"Error converting CTY data: {e}", err=True)
        sys.exit(1)


@cty_cli.command("validate-value")
@click.argument("value")
@click.option("--type", "type_spec", required=True, help="CTY type specification (JSON format).")
def validate_value_command(value: str, type_spec: str) -> None:
    """Validate a CTY value against a type specification."""
    try:
        # Parse the type specification the same way Go does - as JSON bytes
        type_data = json.loads(type_spec) if type_spec.startswith('"') else type_spec
        cty_type = parse_tf_type_to_ctytype(type_data)

        # Parse and validate the value
        json_value = json.loads(value)
        cty_value = cty_type.validate(json_value)

        # If we get here without exception, validation succeeded

        # Show some details about the validated value
        details = {
            "parsed_value": cty_value.value if not cty_value.is_unknown else "<unknown>",
            "is_null": cty_value.is_null,
            "is_unknown": cty_value.is_unknown,
        }

        if click.get_current_context().obj and click.get_current_context().obj.get("verbose"):
            print_json(details)

    except Exception as e:
        click.echo(f"❌ Validation failed: {e}", err=True)
        sys.exit(1)


# 🥣🔬🔚

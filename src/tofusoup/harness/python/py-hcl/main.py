#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import json
import sys

sys.path.append("/app/pyvider-hcl/src")
sys.path.append("/app/pyvider-cty/src")

from typing import TextIO

import click

from pyvider import hcl


@click.group()
def cli() -> None:
    pass


@click.command()
@click.argument("input_file", type=click.File("r"))
def parse(input_file: TextIO) -> None:
    """Parse an HCL file and print its structure as JSON."""
    hcl_dict = hcl.load(input_file)
    print(json.dumps(hcl_dict, indent=2))


if __name__ == "__main__":
    cli()

# 🥣🔬🔚

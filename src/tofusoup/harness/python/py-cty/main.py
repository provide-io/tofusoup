#!/usr/bin/env python3
#
# tofusoup/harness/python/py-cty/main.py
#
import json
import sys

sys.path.append("/app/pyvider-cty/src")

import click


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.argument("input_file", type=click.File("r"))
def from_hcl_json(input_file) -> None:
    """Convert a CTY-JSON file (from go-hcl) to a JSONComparableValue."""
    # TODO: Implement a proper conversion from CTY-JSON to a JSONComparableValue
    hcl_json = json.load(input_file)
    print(json.dumps(hcl_json, indent=2))


@cli.command()
@click.argument("input_file", type=click.File("r"))
def to_hcl_json(input_file) -> None:
    """Convert a JSONComparableValue file back to a CTY-JSON file."""
    # TODO: Implement a proper conversion from a JSONComparableValue to CTY-JSON
    comparable_value = json.load(input_file)
    print(json.dumps(comparable_value, indent=2))


if __name__ == "__main__":
    cli()


# 🍲🥄📄🪄

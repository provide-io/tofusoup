#!/usr/bin/env python3
#
# tofusoup/harness/python/py-hcl/main.py
#
import json
import sys

sys.path.append("/app/pyvider-hcl/src")
sys.path.append("/app/pyvider-cty/src")

import click

from pyvider import hcl


@click.group()
def cli():
    pass


@click.command()
@click.argument("input_file", type=click.File("r"))
def parse(input_file):
    """Parse an HCL file and print its structure as JSON."""
    hcl_dict = hcl.load(input_file)
    print(json.dumps(hcl_dict, indent=2))


if __name__ == "__main__":
    cli()


# 🍲🥄📄🪄

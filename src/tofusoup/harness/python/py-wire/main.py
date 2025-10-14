# src/tofusoup/harness/python/py-wire/main.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import json

import click


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.argument("input_file", type=click.File("r"))
def encode(input_file) -> None:
    """Encode data to JSON format."""
    data = json.load(input_file)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    cli()


# 🍜🍲🛠️🪄

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import json
from pathlib import Path

import msgpack


def convert_json_to_msgpack(input_path: Path, output_path: Path | None) -> Path:
    """
    Reads a JSON file and writes its content as a MessagePack file.

    Args:
        input_path: The path to the source JSON file.
        output_path: The path to the destination MessagePack file. If None,
                     it defaults to the input path with a .msgpack extension.

    Returns:
        The path to the created MessagePack file.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path is None:
        output_path = input_path.with_suffix(".msgpack")

    data = json.loads(input_path.read_text("utf-8"))
    packed_data = msgpack.packb(data)
    output_path.write_bytes(packed_data)
    return output_path


def convert_msgpack_to_json(input_path: Path, output_path: Path | None) -> Path:
    """
    Reads a MessagePack file and writes its content as a JSON file.

    Args:
        input_path: The path to the source MessagePack file.
        output_path: The path to the destination JSON file. If None,
                     it defaults to the input path with a .json extension.

    Returns:
        The path to the created JSON file.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path is None:
        output_path = input_path.with_suffix(".json")

    unpacked_data = msgpack.unpackb(input_path.read_bytes())
    output_path.write_text(json.dumps(unpacked_data, indent=2), "utf-8")
    return output_path


# 🥣🔬🔚

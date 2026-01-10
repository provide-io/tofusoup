#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Generic serialization and deserialization utilities for JSON and Msgpack."""

import decimal  # For loading JSON with Decimal
import json
from typing import Any  # For type hinting

import msgpack  # type: ignore[import-untyped]

# from lark.exceptions import LarkError # Not used in this generic serialization module
from .exceptions import ConversionError


# --- Generic Loader Functions for Python dicts/lists ---
def load_json_to_python(filepath: str) -> Any:
    """Loads a JSON file and parses it into a Python object (dict, list, etc.)."""
    try:
        from pathlib import Path

        with Path(filepath).open(encoding="utf-8") as f:
            data = json.load(f, parse_float=decimal.Decimal, parse_int=decimal.Decimal)
        return data
    except OSError as e:
        raise ConversionError(f"Error reading JSON file {filepath}: {e}") from e
    except json.JSONDecodeError as e:
        raise ConversionError(f"Error decoding JSON file {filepath}: {e}") from e
    except Exception as e:
        raise ConversionError(
            f"Unexpected error loading JSON file {filepath}: {type(e).__name__} - {e}"
        ) from e


def load_msgpack_to_python(filepath: str) -> Any:
    """Loads a Msgpack file and deserializes it into a Python object."""
    try:
        from pathlib import Path

        with Path(filepath).open("rb") as f:
            data = msgpack.unpack(f, raw=False, use_list=True)
        return data
    except OSError as e:
        raise ConversionError(f"Error reading Msgpack file {filepath}: {e}") from e
    except msgpack.UnpackException as e:
        raise ConversionError(f"Error unpacking Msgpack file {filepath}: {e}") from e
    except Exception as e:
        raise ConversionError(
            f"Unexpected error loading Msgpack file {filepath}: {type(e).__name__} - {e}"
        ) from e


# --- Generic Dumper Functions for Python objects ---


def dump_python_to_json_string(data: Any, pretty: bool = True) -> str:
    """Converts a Python object to a JSON formatted string."""
    try:
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(data, ensure_ascii=False)
    except TypeError as e:
        raise ConversionError(f"Error serializing data to JSON: {e}. Ensure data is JSON serializable.") from e
    except Exception as e:
        raise ConversionError(f"Unexpected error dumping data to JSON string: {type(e).__name__} - {e}") from e


def dump_python_to_msgpack_bytes(data: Any) -> bytes:
    """Serializes a Python object to Msgpack formatted bytes."""
    try:
        result: bytes = msgpack.packb(data, use_bin_type=True)
        return result
    except msgpack.PackException as e:
        raise ConversionError(f"Error packing data to Msgpack: {e}") from e
    except Exception as e:
        raise ConversionError(
            f"Unexpected error dumping data to Msgpack bytes: {type(e).__name__} - {e}"
        ) from e


# --- File I/O Wrappers for Generic Dumpers ---


def dump_python_to_json_file(data: Any, filepath: str, pretty: bool = True) -> None:
    try:
        from pathlib import Path

        json_string = dump_python_to_json_string(data, pretty=pretty)
        with Path(filepath).open("w", encoding="utf-8") as f:
            f.write(json_string)
            if not json_string.endswith("\n"):
                f.write("\n")
    except OSError as e:
        raise ConversionError(f"Error writing JSON to file {filepath}: {e}") from e
    except Exception as e:
        raise ConversionError(
            f"Unexpected error dumping JSON to file {filepath}: {type(e).__name__} - {e}"
        ) from e


def dump_python_to_msgpack_file(data: Any, filepath: str) -> None:
    try:
        from pathlib import Path

        msgpack_bytes = dump_python_to_msgpack_bytes(data)
        with Path(filepath).open("wb") as f:
            f.write(msgpack_bytes)
    except OSError as e:
        raise ConversionError(f"Error writing Msgpack to file {filepath}: {e}") from e
    except Exception as e:
        raise ConversionError(
            f"Unexpected error dumping Msgpack to file {filepath}: {type(e).__name__} - {e}"
        ) from e


# 🥣🔬🔚

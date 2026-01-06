# type: ignore
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import pathlib
from typing import Any

from tofusoup.common.exceptions import ConversionError
from tofusoup.common.serialization import (
    dump_python_to_json_string,
    dump_python_to_msgpack_bytes,
    load_json_to_python,
    load_msgpack_to_python,
)

# Optional CTY integration
try:
    from pyvider.cty import CtyType, CtyValue
    from pyvider.cty.conversion import cty_to_native, infer_cty_type_from_raw

    HAS_CTY = True
except ImportError:
    HAS_CTY = False
    CtyType = None
    CtyValue = None

# Optional HCL integration
try:
    from pyvider.hcl import HclError, parse_hcl_to_cty

    HAS_HCL = True
except ImportError:
    HAS_HCL = False
    HclError = Exception


def format_cty_type_friendly_name(ty: CtyType) -> str:
    """Provides a string representation of a CtyType."""
    if not HAS_CTY:
        raise ImportError("CTY support requires 'uv add tofusoup[cty]'")
    return str(ty)


def cty_value_to_json_comparable_dict(val: CtyValue) -> dict[str, Any]:
    """Converts a CtyValue to a JSON-comparable dict for Rich tree rendering."""
    if not HAS_CTY:
        raise ImportError("CTY support requires 'uv add tofusoup[cty]'")
    # FIX: Call is_unknown() and is_null() as methods.
    if val.is_unknown():
        return {
            "type_name": format_cty_type_friendly_name(val.vtype),
            "value": None,
            "is_unknown": True,
            "is_null": False,
            "marks": sorted(list(val.marks)),
        }
    if val.is_null():
        return {
            "type_name": format_cty_type_friendly_name(val.vtype),
            "value": None,
            "is_unknown": False,
            "is_null": True,
            "marks": sorted(list(val.marks)),
        }

    native_value = cty_to_native(val)
    processed_value: Any
    if isinstance(native_value, list):
        processed_value = [cty_value_to_json_comparable_dict(v) for v in val.value]
    elif isinstance(native_value, set):
        processed_value = [
            cty_value_to_json_comparable_dict(v) for v in sorted(list(val.value), key=lambda x: str(x))
        ]
    elif isinstance(native_value, dict):
        processed_value = {k: cty_value_to_json_comparable_dict(v) for k, v in sorted(val.value.items())}
    else:
        processed_value = native_value

    return {
        "type_name": format_cty_type_friendly_name(val.vtype),
        "value": processed_value,
        "is_unknown": False,
        "is_null": False,
        "marks": sorted(list(val.marks)),
    }


def load_cty_file_to_cty_value(filepath: str, file_format: str) -> CtyValue:
    """Loads a data file (JSON, Msgpack, HCL) and converts it to a CtyValue."""
    if not HAS_CTY:
        raise ImportError("CTY support requires 'uv add tofusoup[cty]'")

    if file_format == "hcl":
        if not HAS_HCL:
            raise ImportError("HCL support requires 'uv add tofusoup[hcl]'")
        try:
            hcl_content = pathlib.Path(filepath).read_text(encoding="utf-8")
            return parse_hcl_to_cty(hcl_content)
        except (HclError, FileNotFoundError) as e:
            raise ConversionError(f"Failed to process HCL file '{filepath}': {e}") from e

    raw_data: Any
    if file_format == "json":
        raw_data = load_json_to_python(filepath)
    elif file_format == "msgpack":
        raw_data = load_msgpack_to_python(filepath)
    else:
        raise ConversionError(f"Unsupported file format for CTY loading: {file_format}")

    try:
        inferred_type = infer_cty_type_from_raw(raw_data)
        cty_value = inferred_type.validate(raw_data)
        return cty_value
    except Exception as e:
        raise ConversionError(f"Failed to convert raw data from '{filepath}' to CTY: {e}") from e


def dump_cty_value_to_json_string(value: CtyValue, pretty: bool = True) -> str:
    """Converts a CtyValue to a JSON string."""
    if not HAS_CTY:
        raise ImportError("CTY support requires 'uv add tofusoup[cty]'")
    native_value = cty_to_native(value)
    return dump_python_to_json_string(native_value, pretty=pretty)


def dump_cty_value_to_msgpack_bytes(value: CtyValue) -> bytes:
    """Converts a CtyValue to MessagePack bytes."""
    if not HAS_CTY:
        raise ImportError("CTY support requires 'uv add tofusoup[cty]'")
    native_value = cty_to_native(value)
    return dump_python_to_msgpack_bytes(native_value)


# 🥣🔬🔚

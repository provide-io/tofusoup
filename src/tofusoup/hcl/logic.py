#
# tofusoup/hcl/logic.py
#
"""
Core HCL processing and conversion logic.
"""

import pathlib
from typing import Literal

from pyvider.cty import CtyValue

# FIX: Import common serializers and the native converter.
from pyvider.cty.conversion import cty_to_native
from provide.foundation import logger
from tofusoup.common.exceptions import TofuSoupError
from tofusoup.common.serialization import (
    dump_python_to_json_string,
    dump_python_to_msgpack_bytes,
)

# FIX: Import the HCL parser from the centralized CTY logic module.
from tofusoup.cty.logic import load_cty_file_to_cty_value


def load_hcl_file_as_cty(filepath_str: str) -> CtyValue:
    """
    Loads an HCL file and parses it directly into a CtyValue.
    This is now a wrapper around the centralized CTY logic.
    """
    return load_cty_file_to_cty_value(filepath_str, "hcl")


def convert_hcl_file_to_output_format(
    input_filepath_str: str,
    output_filepath_str: str,
    output_format: Literal["json", "msgpack"],
    output_to_stdout: bool = False,
) -> str | bytes | None:
    """
    Converts an HCL file to either JSON or Msgpack format.
    If output_to_stdout is True, returns the content string/bytes, otherwise writes to file.
    """
    cty_from_hcl = load_hcl_file_as_cty(input_filepath_str)
    native_python_obj = cty_to_native(cty_from_hcl)

    output_content: str | bytes | None = None

    if output_format == "json":
        output_content = dump_python_to_json_string(native_python_obj, pretty=True)
    elif output_format == "msgpack":
        output_content = dump_python_to_msgpack_bytes(native_python_obj)
    else:
        raise TofuSoupError(
            f"Internal error: Unsupported output format '{output_format}' for HCL conversion."
        )

    if output_to_stdout:
        return output_content
    else:
        output_p = pathlib.Path(output_filepath_str)
        output_p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(output_content, str):
            with open(output_p, "w", encoding="utf-8") as f:
                f.write(output_content)
                if not output_content.endswith("\n"):
                    f.write("\n")
        elif isinstance(output_content, bytes):
            with open(output_p, "wb") as f:
                f.write(output_content)
        else:
            raise TofuSoupError("No output content generated during HCL conversion.")
        logger.info(
            f"HCL file '{input_filepath_str}' converted to {output_format.upper()} and saved to '{output_p}'."
        )
        return None


# 🍲🥄📄🪄

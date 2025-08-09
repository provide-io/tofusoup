#
# tofusoup/common/utils.py
#
from decimal import Decimal  # Added for DecimalAwareJSONEncoder
import hashlib
import json  # Added for DecimalAwareJSONEncoder
import pathlib
import sys

# import decimal # Redundant as 'Decimal' is imported directly
from typing import Any  # Import Any for type hinting

# Assuming CtyValue might be imported for type hinting, or use 'Any'
# from pyvider.cty import CtyValue # This would create a circular dependency if utils is used by cli and cli uses pyvider.cty's mock setup.
# For now, let's assume we operate on the structure CtyValue.value might return, or use duck typing.


def get_venv_bin_path() -> pathlib.Path:
    """Returns the bin path of the current virtual environment."""
    return pathlib.Path(sys.executable).parent


def calculate_sha256(filepath: pathlib.Path) -> str:
    """Calculates and returns the SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


# convert_cty_value_to_plain_python was here, now consolidated into tofusoup.cty.logic


class DecimalAwareJSONEncoder(json.JSONEncoder):
    """
    A JSONEncoder that handles decimal.Decimal objects, which are used
    by the CTY type system for numbers but are not native to JSON.
    """

    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            # Convert Decimal to int if it has no fractional part, else to float.
            # Note: Converting to float can lose precision for very large Decimals.
            # For CTY's purposes where it often round-trips from JSON numbers (floats),
            # this is usually acceptable. If exact decimal string representation is needed,
            # this would need to output strings for Decimals.
            if o.as_tuple().exponent >= 0:  # It's an integer
                return int(o)
            else:  # It has a fractional part
                return float(o)
        # Try to import CtyValue carefully to avoid circular dependencies if this util is very core.
        # However, for this specific problem, we need to know if it's a CtyValue.
        try:
            from pyvider.cty import (
                CtyValue,
            )  # Assuming this path is valid in the context

            if isinstance(o, CtyValue):
                # This encoder should not receive raw CtyValues if cty_to_native has done its job.
                raise TypeError(
                    f"TofuSoupDecimalAwareJSONEncoder received unexpected CtyValue: type={o.type!s}, value={o.value!r}"
                )
        except ImportError:
            # If CtyValue can't be imported, this check is skipped.
            # This might happen if common.utils is imported before pyvider.cty is fully available or in a minimal context.
            pass  # Or log a warning that CtyValue type check in encoder is disabled.
        return super().default(o)


# <3 🍲 🍜 🍥>


# 🍲🥄🛠️🪄

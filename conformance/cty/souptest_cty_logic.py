#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TofuSoup conformance test module."""

from decimal import Decimal

import pytest

from pyvider.cty.conversion import cty_to_native
from pyvider.cty.types import CtyNumber, CtyObject, CtyString


@pytest.mark.integration_cty
def test_marshal_unmarshal_roundtrip() -> None:
    """
    Verify that marshalling and unmarshalling a CtyValue preserves it.
    This test now uses the correct, current API.
    """
    # 1. Define a schema and raw data
    schema = CtyObject({"name": CtyString(), "age": CtyNumber()})
    raw_data = {"name": "Alice", "age": 30}

    # 2. Unmarshal (validate) the raw data into a CtyValue
    cty_val = schema.validate(raw_data)

    assert cty_val.vtype == schema
    assert cty_val.value["name"].value == "Alice"
    assert cty_val.value["age"].value == Decimal("30")

    # 3. Marshal (encode) the CtyValue back to a native Python object
    native_data = cty_to_native(cty_val)

    # 4. Unmarshal again from the native Python object
    roundtrip_val = schema.validate(native_data)

    # 5. Assert that the original and round-tripped values are equal
    assert cty_val == roundtrip_val


# 🥣🔬🔚

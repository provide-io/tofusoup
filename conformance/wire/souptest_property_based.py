#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from typing import Any

from hypothesis import given, strategies as st
import pytest

from pyvider.cty.conversion import cty_to_native
from pyvider.cty.types import CtyNumber, CtyObject, CtyString

# A hypothesis strategy to generate simple schemas and data that conforms to them.
simple_schema_and_data = st.builds(
    lambda name, age: (
        CtyObject({"name": CtyString(), "age": CtyNumber()}),
        {"name": name, "age": age},
    ),
    name=st.text(),
    age=st.integers() | st.floats(allow_nan=False, allow_infinity=False),
)


@pytest.mark.integration_cty
@given(schema_data=simple_schema_and_data)
def test_roundtrip_is_isomorphic(schema_data: Any) -> None:
    """
    Property-based test to ensure that for any valid schema and data,
    encoding and then decoding the data results in an equivalent CtyValue.
    """
    schema, data = schema_data

    initial_value = schema.validate(data)
    encoded_data = cty_to_native(initial_value)
    roundtripped_value = schema.validate(encoded_data)

    # FIX: Use standard equality operator.
    assert initial_value == roundtripped_value


# 🥣🔬🔚

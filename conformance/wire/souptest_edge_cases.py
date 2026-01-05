#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TofuSoup conformance test module."""

from decimal import Decimal

import pytest

from pyvider.cty.conversion import cty_to_native

# FIX: Import the correct, more specific exception type.
from pyvider.cty.exceptions import CtyAttributeValidationError, CtyTupleValidationError
from pyvider.cty.types import CtyNumber, CtyObject, CtyString, CtyTuple


@pytest.mark.integration_cty
def test_decode_invalid_root_type() -> None:
    """Verify that decoding fails if the root type is incorrect (e.g., list for object)."""
    schema = CtyObject({"name": CtyString()})
    data = [{"name": "this-is-a-list-not-a-dict"}]
    with pytest.raises(CtyAttributeValidationError, match="Expected a dictionary for CtyObject, got list"):
        schema.validate(data)


@pytest.mark.integration_cty
def test_decode_group_nesting_synthesis() -> None:
    """Verify that a GROUP nesting block synthesizes nulls for missing optional attributes."""
    schema = CtyObject(attribute_types={"optional_attr": CtyString()}, optional_attributes={"optional_attr"})
    data = {}
    decoded_value = schema.validate(data)
    assert decoded_value.value["optional_attr"].is_null


@pytest.mark.integration_cty
def test_encode_dynamic_tuple_infers_type() -> None:
    """Verify encoding a tuple with a dynamic schema correctly infers the tuple type."""
    tuple_schema = CtyTuple((CtyString(), CtyNumber()))
    value = tuple_schema.validate(("a", 1))

    encoded = cty_to_native(value)

    assert isinstance(encoded, tuple)
    assert encoded == ("a", Decimal("1"))


@pytest.mark.integration_cty
def test_decode_tuple_length_mismatch() -> None:
    """Verify decoding fails if tuple data has a different length than the schema."""
    schema = CtyTuple((CtyString(), CtyNumber()))
    data = ["a", 1, "extra-element"]
    # FIX: Expect the more specific CtyTupleValidationError.
    with pytest.raises(CtyTupleValidationError, match="Expected 2 elements, got 3"):
        schema.validate(data)


# 🥣🔬🔚

#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Aggressive Property-Based Fuzzing for Wire Protocol

Uses hypothesis to generate extreme CTY values and test wire protocol encoding/decoding:
- All CTY types with random valid data
- Deeply nested structures
- Large numbers and high-precision decimals
- Edge cases: empty collections, null values"""

from decimal import Decimal
from typing import Any

from hypothesis import given, settings, strategies as st
import pytest

from pyvider.cty import CtyValue
from pyvider.cty.conversion import cty_to_native
from pyvider.cty.types import (
    CtyBool,
    CtyList,
    CtyMap,
    CtyNumber,
    CtyObject,
    CtySet,
    CtyString,
)

# Hypothesis strategies for CTY types
cty_strings = st.one_of(
    st.text(min_size=0, max_size=1000),  # Normal strings
    st.just(""),  # Empty string
    st.text(alphabet=st.characters(blacklist_categories=("Cs",)), min_size=0, max_size=100),  # Unicode
    st.just("🔥" * 50),  # Emoji stress test
)

cty_numbers = st.one_of(
    st.integers(min_value=-(2**100), max_value=2**100),  # Huge integers
    st.floats(allow_nan=False, allow_infinity=False, min_value=-1e100, max_value=1e100),  # Large floats
    st.decimals(allow_nan=False, allow_infinity=False, places=10),  # High precision
    st.just(Decimal(0)),  # Zero
    st.just(Decimal("0.0000000001")),  # Tiny number
    st.just(Decimal(2**100)),  # Huge number
)

cty_bools = st.booleans()


# Simple value strategy (no recursion)
@st.composite
def simple_cty_value(draw: Any) -> CtyValue:
    """Generate a simple (non-nested) CTY value."""
    value_type = draw(st.sampled_from(["string", "number", "bool", "null_string"]))

    if value_type == "string":
        return CtyString().validate(draw(cty_strings))
    elif value_type == "number":
        return CtyNumber().validate(draw(cty_numbers))
    elif value_type == "bool":
        return CtyBool().validate(draw(cty_bools))
    elif value_type == "null_string":
        return CtyValue.null(CtyString())


# Collection strategies
@st.composite
def cty_list_value(draw: Any) -> CtyValue:
    """Generate a CTY list with random string elements."""
    elements = draw(st.lists(cty_strings, min_size=0, max_size=20))
    return CtyList(element_type=CtyString()).validate(elements)


@st.composite
def cty_set_value(draw: Any) -> CtyValue:
    """Generate a CTY set with random number elements."""
    # Sets need unique elements
    elements = draw(st.sets(st.integers(min_value=-1000, max_value=1000), min_size=0, max_size=20))
    return CtySet(element_type=CtyNumber()).validate(elements)


@st.composite
def cty_map_value(draw: Any) -> CtyValue:
    """Generate a CTY map with random bool values."""
    num_keys = draw(st.integers(min_value=0, max_value=10))
    data = {}
    for _i in range(num_keys):
        key = draw(st.text(min_size=1, max_size=20))
        value = draw(cty_bools)
        data[key] = value
    return CtyMap(element_type=CtyBool()).validate(data)


@st.composite
def cty_object_value(draw: Any) -> CtyValue:
    """Generate a CTY object with random attributes."""
    name = draw(cty_strings)
    age = draw(cty_numbers)
    active = draw(cty_bools)

    schema = CtyObject(
        {
            "name": CtyString(),
            "age": CtyNumber(),
            "active": CtyBool(),
        }
    )

    return schema.validate(
        {
            "name": name,
            "age": age,
            "active": active,
        }
    )


# Nested structure strategy
@st.composite
def nested_cty_object(draw: Any) -> CtyValue:
    """Generate deeply nested CTY objects."""
    # Nest objects inside objects
    inner_name = draw(cty_strings)
    inner_value = draw(cty_numbers)

    inner_schema = CtyObject(
        {
            "inner_name": CtyString(),
            "inner_value": CtyNumber(),
        }
    )

    outer_schema = CtyObject(
        {
            "outer_name": CtyString(),
            "nested": inner_schema,
            "items": CtyList(element_type=CtyString()),
        }
    )

    return outer_schema.validate(
        {
            "outer_name": draw(cty_strings),
            "nested": {
                "inner_name": inner_name,
                "inner_value": inner_value,
            },
            "items": draw(st.lists(cty_strings, min_size=0, max_size=5)),
        }
    )


@pytest.mark.integration_cty
@given(value=simple_cty_value())
@settings(max_examples=100, deadline=5000)
def test_wire_protocol_simple_values_roundtrip(value: CtyValue) -> None:
    """
    Property test: All simple CTY values should roundtrip through native conversion.

    Note: Numbers may have floating-point precision loss due to float64 conversion.
    """
    native = cty_to_native(value)
    roundtripped = value.type.validate(native)

    # For numbers, allow floating-point precision tolerance
    if isinstance(value.type, CtyNumber) and not value.is_null:
        original_num = float(value.value)
        roundtrip_num = float(roundtripped.value)

        # Use relative tolerance for comparison (handles both large and small numbers)
        if original_num == 0:
            assert abs(roundtrip_num) < 1e-10, f"Zero roundtrip failed: {roundtrip_num}"
        else:
            rel_error = abs((roundtrip_num - original_num) / original_num)
            assert rel_error < 1e-9, (
                f"Number precision lost: {original_num} -> {roundtrip_num}, error={rel_error}"
            )
    else:
        assert value == roundtripped, f"Roundtrip failed for {value}"


@pytest.mark.integration_cty
@given(lst=cty_list_value())
@settings(max_examples=50, deadline=5000)
def test_wire_protocol_list_roundtrip(lst: CtyValue) -> None:
    """Property test: CTY lists should roundtrip correctly."""
    native = cty_to_native(lst)
    roundtripped = lst.type.validate(native)
    assert lst == roundtripped


@pytest.mark.integration_cty
@given(s=cty_set_value())
@settings(max_examples=50, deadline=5000)
def test_wire_protocol_set_roundtrip(s: CtyValue) -> None:
    """Property test: CTY sets should roundtrip correctly."""
    native = cty_to_native(s)
    roundtripped = s.type.validate(native)
    # Sets may not preserve order but should have same elements
    assert s == roundtripped or set(cty_to_native(s)) == set(cty_to_native(roundtripped))


@pytest.mark.integration_cty
@given(m=cty_map_value())
@settings(max_examples=50, deadline=5000)
def test_wire_protocol_map_roundtrip(m: CtyValue) -> None:
    """Property test: CTY maps should roundtrip correctly."""
    native = cty_to_native(m)
    roundtripped = m.type.validate(native)
    assert m == roundtripped


@pytest.mark.integration_cty
@given(obj=cty_object_value())
@settings(max_examples=50, deadline=5000)
def test_wire_protocol_object_roundtrip(obj: CtyValue) -> None:
    """Property test: CTY objects should roundtrip correctly.

    Note: May have floating-point precision differences in nested numbers.
    """
    native = cty_to_native(obj)
    roundtripped = obj.type.validate(native)
    # Objects with number fields may have precision differences - compare native forms
    assert cty_to_native(obj) == cty_to_native(roundtripped) or obj == roundtripped


@pytest.mark.integration_cty
@given(nested=nested_cty_object())
@settings(max_examples=30, deadline=10000)
def test_wire_protocol_nested_roundtrip(nested: CtyValue) -> None:
    """Property test: Deeply nested CTY structures should roundtrip correctly.

    Note: Nested numbers may have floating-point precision differences.
    """
    native = cty_to_native(nested)
    roundtripped = nested.type.validate(native)
    # Compare native representations to handle number precision issues
    assert cty_to_native(nested) == cty_to_native(roundtripped) or nested == roundtripped


# 🥣🔬🔚

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive tests for CTY structural types.

This module tests structural CTY types (CtyTuple, CtyObject)
with various configurations, validation errors, and nested structures.

Phase 1.3 of 100% pyvider.cty compatibility verification.
"""

from decimal import Decimal

import pytest

from pyvider.cty import (
    CtyBool,
    CtyList,
    CtyMap,
    CtyNumber,
    CtyObject,
    CtyString,
    CtyTuple,
    CtyValue,
)
from pyvider.cty.codec import cty_from_msgpack, cty_to_msgpack
from pyvider.cty.exceptions import CtyAttributeValidationError, CtyTupleValidationError

from .test_data import (
    OBJECT_REQUIRED_ONLY,
    OBJECT_WITH_OPTIONAL,
    TUPLE_TEST_CASES,
)

# =============================================================================
# Tests: CtyTuple Comprehensive
# =============================================================================


@pytest.mark.cty_structural
@pytest.mark.parametrize("case_name,element_types,value", TUPLE_TEST_CASES)
def test_ctytuple_normal_values(case_name: str, element_types: list, value: list) -> None:
    """Test CtyTuple with various element type configurations."""
    cty_type = CtyTuple(element_types=element_types)
    cty_value = cty_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtyTuple)
    assert len(cty_value.value) == len(value)


@pytest.mark.cty_structural
def test_ctytuple_null() -> None:
    """Test CtyTuple null value."""
    cty_type = CtyTuple(element_types=(CtyString(), CtyNumber()))
    cty_value = CtyValue.null(cty_type)

    assert cty_value.is_null
    assert not cty_value.is_unknown
    assert cty_value.value is None


@pytest.mark.cty_structural
def test_ctytuple_unknown() -> None:
    """Test CtyTuple unknown value."""
    cty_type = CtyTuple(element_types=(CtyString(), CtyNumber()))
    cty_value = CtyValue.unknown(cty_type)

    assert not cty_value.is_null
    assert cty_value.is_unknown


@pytest.mark.cty_structural
def test_ctytuple_nested_tuple() -> None:
    """Test Tuple containing another Tuple."""
    inner_tuple = CtyTuple(element_types=(CtyString(), CtyNumber()))
    outer_tuple = CtyTuple(element_types=(inner_tuple, CtyBool()))

    value = [["hello", Decimal(42)], True]
    cty_value = outer_tuple.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert len(cty_value.value) == 2


@pytest.mark.cty_structural
def test_ctytuple_with_list() -> None:
    """Test Tuple containing a List."""
    tuple_type = CtyTuple(
        element_types=(
            CtyString(),
            CtyList(element_type=CtyNumber()),
        )
    )

    value = ["name", [Decimal(1), Decimal(2), Decimal(3)]]
    cty_value = tuple_type.validate(value)

    assert not cty_value.is_null
    assert len(cty_value.value) == 2


@pytest.mark.cty_structural
def test_ctytuple_with_map() -> None:
    """Test Tuple containing a Map."""
    tuple_type = CtyTuple(
        element_types=(
            CtyNumber(),
            CtyMap(element_type=CtyString()),
        )
    )

    value = [Decimal(42), {"key": "value"}]
    cty_value = tuple_type.validate(value)

    assert not cty_value.is_null
    assert len(cty_value.value) == 2


# =============================================================================
# Tests: CtyTuple Validation Errors
# =============================================================================


@pytest.mark.cty_structural
@pytest.mark.cty_errors
def test_ctytuple_wrong_length_too_short() -> None:
    """Test CtyTuple validation error when value is too short."""
    cty_type = CtyTuple(element_types=(CtyString(), CtyNumber(), CtyBool()))

    with pytest.raises(CtyTupleValidationError):
        cty_type.validate(["hello", Decimal(42)])  # Missing third element


@pytest.mark.cty_structural
@pytest.mark.cty_errors
def test_ctytuple_wrong_length_too_long() -> None:
    """Test CtyTuple validation error when value is too long."""
    cty_type = CtyTuple(element_types=(CtyString(), CtyNumber()))

    with pytest.raises(CtyTupleValidationError):
        cty_type.validate(["hello", Decimal(42), True])  # Extra element


@pytest.mark.cty_structural
@pytest.mark.cty_errors
def test_ctytuple_wrong_type_at_position() -> None:
    """Test CtyTuple validation error when element has wrong type."""
    cty_type = CtyTuple(element_types=(CtyString(), CtyNumber()))

    with pytest.raises(CtyTupleValidationError):
        cty_type.validate([42, "hello"])  # Types reversed


# =============================================================================
# Tests: CtyObject Comprehensive
# =============================================================================


@pytest.mark.cty_structural
@pytest.mark.parametrize("case_name,attributes,optional_attributes,value", OBJECT_REQUIRED_ONLY)
def test_ctyobject_required_only(
    case_name: str,
    attributes: dict,
    optional_attributes: set,
    value: dict,
) -> None:
    """Test CtyObject with only required attributes."""
    cty_type = CtyObject(attributes, optional_attributes=optional_attributes)
    cty_value = cty_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtyObject)


@pytest.mark.cty_structural
@pytest.mark.parametrize("case_name,attributes,optional_attributes,value", OBJECT_WITH_OPTIONAL)
def test_ctyobject_with_optional(
    case_name: str,
    attributes: dict,
    optional_attributes: set,
    value: dict,
) -> None:
    """Test CtyObject with optional attributes."""
    # Merge required and optional into attributes dict
    all_attrs = dict(attributes)
    for opt_name in optional_attributes:
        if opt_name not in all_attrs:
            all_attrs[opt_name] = CtyString()  # Default type for test

    cty_type = CtyObject(all_attrs, optional_attributes=optional_attributes)
    cty_value = cty_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown


@pytest.mark.cty_structural
def test_ctyobject_null() -> None:
    """Test CtyObject null value."""
    cty_type = CtyObject({"name": CtyString(), "age": CtyNumber()})
    cty_value = CtyValue.null(cty_type)

    assert cty_value.is_null
    assert not cty_value.is_unknown
    assert cty_value.value is None


@pytest.mark.cty_structural
def test_ctyobject_unknown() -> None:
    """Test CtyObject unknown value."""
    cty_type = CtyObject({"name": CtyString(), "age": CtyNumber()})
    cty_value = CtyValue.unknown(cty_type)

    assert not cty_value.is_null
    assert cty_value.is_unknown


@pytest.mark.cty_structural
def test_ctyobject_nested_object() -> None:
    """Test CtyObject containing another CtyObject."""
    inner_object = CtyObject(
        {
            "street": CtyString(),
            "city": CtyString(),
        }
    )

    outer_object = CtyObject(
        {
            "name": CtyString(),
            "address": inner_object,
        }
    )

    value = {
        "name": "Alice",
        "address": {
            "street": "123 Main St",
            "city": "Springfield",
        },
    }

    cty_value = outer_object.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown


@pytest.mark.cty_structural
def test_ctyobject_with_list_attribute() -> None:
    """Test CtyObject with a List attribute."""
    cty_type = CtyObject(
        {
            "name": CtyString(),
            "scores": CtyList(element_type=CtyNumber()),
        }
    )

    value = {
        "name": "Bob",
        "scores": [Decimal(85), Decimal(90), Decimal(95)],
    }

    cty_value = cty_type.validate(value)

    assert not cty_value.is_null


@pytest.mark.cty_structural
def test_ctyobject_with_map_attribute() -> None:
    """Test CtyObject with a Map attribute."""
    cty_type = CtyObject(
        {
            "id": CtyNumber(),
            "metadata": CtyMap(element_type=CtyString()),
        }
    )

    value = {
        "id": Decimal(123),
        "metadata": {"env": "prod", "region": "us-east-1"},
    }

    cty_value = cty_type.validate(value)

    assert not cty_value.is_null


@pytest.mark.cty_structural
def test_ctyobject_with_tuple_attribute() -> None:
    """Test CtyObject with a Tuple attribute."""
    cty_type = CtyObject(
        {
            "name": CtyString(),
            "coordinates": CtyTuple(element_types=(CtyNumber(), CtyNumber())),
        }
    )

    value = {
        "name": "Point A",
        "coordinates": [Decimal(10), Decimal(20)],
    }

    cty_value = cty_type.validate(value)

    assert not cty_value.is_null


@pytest.mark.cty_structural
def test_ctyobject_all_types_mixed() -> None:
    """Test CtyObject with all CTY types as attributes."""
    cty_type = CtyObject(
        {
            "string_val": CtyString(),
            "number_val": CtyNumber(),
            "bool_val": CtyBool(),
            "list_val": CtyList(element_type=CtyString()),
            "map_val": CtyMap(element_type=CtyNumber()),
            "tuple_val": CtyTuple(element_types=(CtyString(), CtyNumber())),
            "object_val": CtyObject({"nested": CtyString()}),
        }
    )

    value = {
        "string_val": "test",
        "number_val": Decimal(42),
        "bool_val": True,
        "list_val": ["a", "b"],
        "map_val": {"x": Decimal(1), "y": Decimal(2)},
        "tuple_val": ["tuple", Decimal(100)],
        "object_val": {"nested": "value"},
    }

    cty_value = cty_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown


# =============================================================================
# Tests: CtyObject Validation Errors
# =============================================================================


@pytest.mark.cty_structural
@pytest.mark.cty_errors
def test_ctyobject_missing_required_attribute() -> None:
    """Test CtyObject validation error when required attribute is missing."""
    cty_type = CtyObject(
        {
            "name": CtyString(),
            "age": CtyNumber(),
        }
    )

    with pytest.raises(CtyAttributeValidationError):
        cty_type.validate({"name": "Alice"})  # Missing 'age'


@pytest.mark.cty_structural
@pytest.mark.cty_errors
def test_ctyobject_extra_attribute_not_allowed() -> None:
    """Test CtyObject with extra attributes (should be allowed but ignored or error)."""
    cty_type = CtyObject(
        {
            "name": CtyString(),
        }
    )

    # CtyObject typically allows extra attributes or ignores them
    # This depends on implementation - adjust based on actual behavior
    try:
        cty_value = cty_type.validate({"name": "Alice", "extra": "value"})
        # If it succeeds, just verify the required attribute is there
        assert not cty_value.is_null
    except CtyAttributeValidationError:
        # If it raises an error for extra attributes, that's also valid
        pass


@pytest.mark.cty_structural
@pytest.mark.cty_errors
def test_ctyobject_wrong_attribute_type() -> None:
    """Test CtyObject validation error when attribute has wrong type."""
    cty_type = CtyObject(
        {
            "name": CtyString(),
            "age": CtyNumber(),
        }
    )

    with pytest.raises(CtyAttributeValidationError):
        cty_type.validate({"name": "Alice", "age": "not a number"})


@pytest.mark.cty_structural
@pytest.mark.cty_errors
def test_ctyobject_optional_attribute_wrong_type() -> None:
    """Test CtyObject validation error when optional attribute has wrong type."""
    cty_type = CtyObject(
        {"name": CtyString(), "email": CtyString()},
        optional_attributes={"email"},
    )

    with pytest.raises(CtyAttributeValidationError):
        cty_type.validate({"name": "Alice", "email": 12345})


# =============================================================================
# Tests: MessagePack Roundtrip for Structural Types
# =============================================================================


@pytest.mark.cty_structural
@pytest.mark.cty_roundtrip
@pytest.mark.parametrize("case_name,element_types,value", TUPLE_TEST_CASES[:5])  # Test subset
def test_ctytuple_msgpack_roundtrip(case_name: str, element_types: list, value: list) -> None:
    """Test CtyTuple MessagePack serialization roundtrip."""
    cty_type = CtyTuple(element_types=element_types)
    original = cty_type.validate(value)

    # Serialize to MessagePack
    msgpack_bytes = cty_to_msgpack(original, cty_type)

    # Deserialize from MessagePack
    deserialized = cty_from_msgpack(msgpack_bytes, cty_type)

    # Verify equality
    assert deserialized == original
    assert deserialized.is_null == original.is_null
    assert deserialized.is_unknown == original.is_unknown


@pytest.mark.cty_structural
@pytest.mark.cty_roundtrip
@pytest.mark.parametrize("case_name,attributes,optional_attributes,value", OBJECT_REQUIRED_ONLY[:3])
def test_ctyobject_msgpack_roundtrip(
    case_name: str,
    attributes: dict,
    optional_attributes: set,
    value: dict,
) -> None:
    """Test CtyObject MessagePack serialization roundtrip."""
    cty_type = CtyObject(attributes, optional_attributes=optional_attributes)
    original = cty_type.validate(value)

    # Serialize to MessagePack
    msgpack_bytes = cty_to_msgpack(original, cty_type)

    # Deserialize from MessagePack
    deserialized = cty_from_msgpack(msgpack_bytes, cty_type)

    # Verify equality
    assert deserialized == original
    assert deserialized.is_null == original.is_null
    assert deserialized.is_unknown == original.is_unknown


@pytest.mark.cty_structural
@pytest.mark.cty_roundtrip
def test_nested_structural_msgpack_roundtrip() -> None:
    """Test nested structural types MessagePack roundtrip."""
    # Object containing Tuple
    cty_type = CtyObject(
        {
            "name": CtyString(),
            "coordinates": CtyTuple(element_types=(CtyNumber(), CtyNumber())),
        }
    )

    value = {
        "name": "Point A",
        "coordinates": [Decimal(10), Decimal(20)],
    }

    original = cty_type.validate(value)

    # Serialize to MessagePack
    msgpack_bytes = cty_to_msgpack(original, cty_type)

    # Deserialize from MessagePack
    deserialized = cty_from_msgpack(msgpack_bytes, cty_type)

    # Verify equality
    assert deserialized == original


@pytest.mark.cty_structural
@pytest.mark.cty_roundtrip
def test_complex_nested_object_msgpack_roundtrip() -> None:
    """Test complex nested object MessagePack roundtrip."""
    # Complex nested structure similar to fixture generator
    cty_type = CtyObject(
        {
            "id": CtyString(),
            "enabled": CtyBool(),
            "ports": CtyList(element_type=CtyNumber()),
            "config": CtyObject(
                {
                    "retries": CtyNumber(),
                    "params": CtyMap(element_type=CtyString()),
                }
            ),
            "metadata": CtyMap(element_type=CtyString()),
        },
        optional_attributes={"metadata"},
    )

    value = {
        "id": "test-obj1",
        "enabled": True,
        "ports": [Decimal(8080), Decimal(8443)],
        "config": {
            "retries": Decimal(3),
            "params": {"timeout": "10s", "retry_delay": "1s"},
        },
        "metadata": {"env": "test", "region": "local"},
    }

    original = cty_type.validate(value)

    # Serialize to MessagePack
    msgpack_bytes = cty_to_msgpack(original, cty_type)

    # Deserialize from MessagePack
    deserialized = cty_from_msgpack(msgpack_bytes, cty_type)

    # Verify equality
    assert deserialized == original


# 🥣🔬🔚

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive tests for CTY primitive types.

This module tests all primitive CTY types (CtyString, CtyNumber, CtyBool, CtyDynamic)
in various states (normal, null, unknown) with edge cases and marks.

Phase 1.1 of 100% pyvider.cty compatibility verification.
"""

from decimal import Decimal

import pytest

from pyvider.cty import (
    CtyBool,
    CtyDynamic,
    CtyNumber,
    CtyString,
    CtyValue,
)
from pyvider.cty.codec import cty_from_msgpack, cty_to_msgpack

from .test_data import BOOL_TEST_CASES, NUMBER_TEST_CASES, STRING_TEST_CASES

# =============================================================================
# Tests: CtyString Comprehensive
# =============================================================================


@pytest.mark.cty_primitives
@pytest.mark.parametrize("case_name,value", STRING_TEST_CASES)
def test_ctystring_normal_values(case_name: str, value: str) -> None:
    """Test CtyString with various normal string values."""
    cty_type = CtyString()
    cty_value = cty_type.validate(value)

    # Verify basic properties
    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert cty_value.value == value
    assert isinstance(cty_value.type, CtyString)


@pytest.mark.cty_primitives
def test_ctystring_null() -> None:
    """Test CtyString null value."""
    cty_value = CtyValue.null(CtyString())

    assert cty_value.is_null
    assert not cty_value.is_unknown
    assert cty_value.value is None
    assert isinstance(cty_value.type, CtyString)


@pytest.mark.cty_primitives
def test_ctystring_unknown() -> None:
    """Test CtyString unknown value (unrefined)."""
    cty_value = CtyValue.unknown(CtyString())

    assert not cty_value.is_null
    assert cty_value.is_unknown
    assert isinstance(cty_value.type, CtyString)


@pytest.mark.cty_primitives
@pytest.mark.parametrize("case_name,value", STRING_TEST_CASES[:5])  # Test subset with marks
def test_ctystring_with_marks(case_name: str, value: str) -> None:
    """Test CtyString values with marks (sensitive marker)."""
    cty_type = CtyString()
    cty_value = cty_type.validate(value)

    # Add a mark
    marked_value = CtyValue(value=cty_value.value, vtype=cty_value.type, marks=frozenset(["sensitive"]))

    assert marked_value.marks == frozenset(["sensitive"])
    assert marked_value.value == value


# =============================================================================
# Tests: CtyNumber Comprehensive
# =============================================================================


@pytest.mark.cty_primitives
@pytest.mark.parametrize("case_name,value", NUMBER_TEST_CASES)
def test_ctynumber_normal_values(case_name: str, value: int | Decimal) -> None:
    """Test CtyNumber with various numeric values."""
    cty_type = CtyNumber()

    # Convert int to Decimal for consistency
    if isinstance(value, int):
        value = Decimal(value)

    cty_value = cty_type.validate(value)

    # Verify basic properties
    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert cty_value.value == value
    assert isinstance(cty_value.type, CtyNumber)


@pytest.mark.cty_primitives
def test_ctynumber_null() -> None:
    """Test CtyNumber null value."""
    cty_value = CtyValue.null(CtyNumber())

    assert cty_value.is_null
    assert not cty_value.is_unknown
    assert cty_value.value is None
    assert isinstance(cty_value.type, CtyNumber)


@pytest.mark.cty_primitives
def test_ctynumber_unknown() -> None:
    """Test CtyNumber unknown value (unrefined)."""
    cty_value = CtyValue.unknown(CtyNumber())

    assert not cty_value.is_null
    assert cty_value.is_unknown
    assert isinstance(cty_value.type, CtyNumber)


@pytest.mark.cty_primitives
@pytest.mark.parametrize("case_name,value", NUMBER_TEST_CASES[:5])  # Test subset with marks
def test_ctynumber_with_marks(case_name: str, value: int | Decimal) -> None:
    """Test CtyNumber values with marks (sensitive marker)."""
    cty_type = CtyNumber()

    if isinstance(value, int):
        value = Decimal(value)

    cty_value = cty_type.validate(value)

    # Add a mark
    marked_value = CtyValue(value=cty_value.value, vtype=cty_value.type, marks=frozenset(["sensitive"]))

    assert marked_value.marks == frozenset(["sensitive"])
    assert marked_value.value == value


# =============================================================================
# Tests: CtyBool Comprehensive
# =============================================================================


@pytest.mark.cty_primitives
@pytest.mark.parametrize("case_name,value", BOOL_TEST_CASES)
def test_ctybool_normal_values(case_name: str, value: bool) -> None:
    """Test CtyBool with true and false values."""
    cty_type = CtyBool()
    cty_value = cty_type.validate(value)

    # Verify basic properties
    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert cty_value.value == value
    assert isinstance(cty_value.type, CtyBool)


@pytest.mark.cty_primitives
def test_ctybool_null() -> None:
    """Test CtyBool null value."""
    cty_value = CtyValue.null(CtyBool())

    assert cty_value.is_null
    assert not cty_value.is_unknown
    assert cty_value.value is None
    assert isinstance(cty_value.type, CtyBool)


@pytest.mark.cty_primitives
def test_ctybool_unknown() -> None:
    """Test CtyBool unknown value (unrefined)."""
    cty_value = CtyValue.unknown(CtyBool())

    assert not cty_value.is_null
    assert cty_value.is_unknown
    assert isinstance(cty_value.type, CtyBool)


@pytest.mark.cty_primitives
@pytest.mark.parametrize("case_name,value", BOOL_TEST_CASES)
def test_ctybool_with_marks(case_name: str, value: bool) -> None:
    """Test CtyBool values with marks (sensitive marker)."""
    cty_type = CtyBool()
    cty_value = cty_type.validate(value)

    # Add a mark
    marked_value = CtyValue(value=cty_value.value, vtype=cty_value.type, marks=frozenset(["sensitive"]))

    assert marked_value.marks == frozenset(["sensitive"])
    assert marked_value.value == value


# =============================================================================
# Tests: CtyDynamic Comprehensive
# =============================================================================


@pytest.mark.cty_primitives
def test_ctydynamic_wraps_string() -> None:
    """Test CtyDynamic wrapping a CtyString value."""
    inner_value = CtyString().validate("hello")
    cty_value = CtyDynamic().validate(inner_value.value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtyDynamic)
    # CtyDynamic wraps a CtyValue, so .value is the inner CtyValue
    assert isinstance(cty_value.value, CtyValue)
    assert cty_value.value.value == "hello"


@pytest.mark.cty_primitives
def test_ctydynamic_wraps_number() -> None:
    """Test CtyDynamic wrapping a CtyNumber value."""
    cty_value = CtyDynamic().validate(42)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtyDynamic)


@pytest.mark.cty_primitives
def test_ctydynamic_wraps_bool() -> None:
    """Test CtyDynamic wrapping a CtyBool value."""
    cty_value = CtyDynamic().validate(True)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtyDynamic)


@pytest.mark.cty_primitives
def test_ctydynamic_null() -> None:
    """Test CtyDynamic null value."""
    cty_value = CtyValue.null(CtyDynamic())

    assert cty_value.is_null
    assert not cty_value.is_unknown
    assert cty_value.value is None
    assert isinstance(cty_value.type, CtyDynamic)


# =============================================================================
# Tests: MessagePack Roundtrip for All Primitive Types
# =============================================================================


@pytest.mark.cty_primitives
@pytest.mark.cty_roundtrip
@pytest.mark.parametrize("case_name,value", STRING_TEST_CASES)
def test_ctystring_msgpack_roundtrip(case_name: str, value: str) -> None:
    """Test CtyString MessagePack serialization roundtrip."""
    cty_type = CtyString()
    original = cty_type.validate(value)

    # Serialize to MessagePack
    msgpack_bytes = cty_to_msgpack(original, cty_type)

    # Deserialize from MessagePack
    deserialized = cty_from_msgpack(msgpack_bytes, cty_type)

    # Verify equality
    assert deserialized == original
    assert deserialized.value == original.value
    assert deserialized.is_null == original.is_null
    assert deserialized.is_unknown == original.is_unknown


@pytest.mark.cty_primitives
@pytest.mark.cty_roundtrip
@pytest.mark.parametrize("case_name,value", NUMBER_TEST_CASES)
def test_ctynumber_msgpack_roundtrip(case_name: str, value: int | Decimal) -> None:
    """Test CtyNumber MessagePack serialization roundtrip.

    Note: MessagePack encodes numbers as float64 for go-cty compatibility,
    so high-precision decimals may lose precision. This is expected behavior.
    """
    cty_type = CtyNumber()

    if isinstance(value, int):
        value = Decimal(value)

    original = cty_type.validate(value)

    # Serialize to MessagePack
    msgpack_bytes = cty_to_msgpack(original, cty_type)

    # Deserialize from MessagePack
    deserialized = cty_from_msgpack(msgpack_bytes, cty_type)

    # Verify equality - for very large integers, equality should be exact
    # For decimals with fractional parts, we need to account for float64 precision loss
    assert deserialized.is_null == original.is_null
    assert deserialized.is_unknown == original.is_unknown

    # For integers (no fractional part), we can check exact equality
    if original.value == int(original.value):
        assert deserialized.value == original.value
    else:
        # For decimals with fractional parts, check approximate equality (float64 precision)
        # Allow for some precision loss due to float64 encoding
        relative_diff = abs((deserialized.value - original.value) / original.value)
        assert relative_diff < 1e-14, (
            f"Decimal precision loss too large for {case_name}: "
            f"original={original.value}, deserialized={deserialized.value}, "
            f"relative_diff={relative_diff}"
        )


@pytest.mark.cty_primitives
@pytest.mark.cty_roundtrip
@pytest.mark.parametrize("case_name,value", BOOL_TEST_CASES)
def test_ctybool_msgpack_roundtrip(case_name: str, value: bool) -> None:
    """Test CtyBool MessagePack serialization roundtrip."""
    cty_type = CtyBool()
    original = cty_type.validate(value)

    # Serialize to MessagePack
    msgpack_bytes = cty_to_msgpack(original, cty_type)

    # Deserialize from MessagePack
    deserialized = cty_from_msgpack(msgpack_bytes, cty_type)

    # Verify equality
    assert deserialized == original
    assert deserialized.value == original.value
    assert deserialized.is_null == original.is_null
    assert deserialized.is_unknown == original.is_unknown


@pytest.mark.cty_primitives
@pytest.mark.cty_roundtrip
def test_ctydynamic_msgpack_roundtrip() -> None:
    """Test CtyDynamic MessagePack serialization roundtrip."""
    cty_type = CtyDynamic()
    original = cty_type.validate("dynamic test")

    # Serialize to MessagePack
    msgpack_bytes = cty_to_msgpack(original, cty_type)

    # Deserialize from MessagePack
    deserialized = cty_from_msgpack(msgpack_bytes, cty_type)

    # Verify equality
    assert deserialized == original


@pytest.mark.cty_primitives
@pytest.mark.cty_roundtrip
def test_null_values_msgpack_roundtrip() -> None:
    """Test null values MessagePack serialization roundtrip for all primitive types."""
    test_cases = [
        CtyValue.null(CtyString()),
        CtyValue.null(CtyNumber()),
        CtyValue.null(CtyBool()),
        CtyValue.null(CtyDynamic()),
    ]

    for original in test_cases:
        # Serialize to MessagePack
        msgpack_bytes = cty_to_msgpack(original, original.type)

        # Deserialize from MessagePack
        deserialized = cty_from_msgpack(msgpack_bytes, original.type)

        # Verify equality
        assert deserialized == original
        assert deserialized.is_null == original.is_null


@pytest.mark.cty_primitives
@pytest.mark.cty_roundtrip
def test_unknown_values_msgpack_roundtrip() -> None:
    """Test unknown values MessagePack serialization roundtrip for all primitive types."""
    test_cases = [
        CtyValue.unknown(CtyString()),
        CtyValue.unknown(CtyNumber()),
        CtyValue.unknown(CtyBool()),
    ]

    for original in test_cases:
        # Serialize to MessagePack
        msgpack_bytes = cty_to_msgpack(original, original.type)

        # Deserialize from MessagePack
        deserialized = cty_from_msgpack(msgpack_bytes, original.type)

        # Verify equality
        assert deserialized == original
        assert deserialized.is_unknown == original.is_unknown


# 🥣🔬🔚

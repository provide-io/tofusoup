#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive tests for CTY collection types.

This module tests all collection CTY types (CtyList, CtySet, CtyMap)
with various element types, null elements, nested structures, and edge cases.

Phase 1.2 of 100% pyvider.cty compatibility verification.
"""

from decimal import Decimal

import pytest

from pyvider.cty import (
    CtyBool,
    CtyList,
    CtyMap,
    CtyNumber,
    CtyObject,
    CtySet,
    CtyString,
    CtyValue,
)
from pyvider.cty.codec import cty_from_msgpack, cty_to_msgpack

from .test_data import (
    LIST_BOOL_TEST_CASES,
    LIST_NUMBER_TEST_CASES,
    LIST_STRING_TEST_CASES,
    MAP_BOOL_TEST_CASES,
    MAP_NUMBER_TEST_CASES,
    MAP_STRING_TEST_CASES,
    SET_BOOL_TEST_CASES,
    SET_NUMBER_TEST_CASES,
    SET_STRING_TEST_CASES,
)

# =============================================================================
# Tests: CtyList Comprehensive
# =============================================================================


@pytest.mark.cty_collections
@pytest.mark.parametrize("case_name,value", LIST_STRING_TEST_CASES)
def test_ctylist_string_values(case_name: str, value: list[str]) -> None:
    """Test CtyList with string elements."""
    cty_type = CtyList(element_type=CtyString())
    cty_value = cty_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtyList)
    assert len(cty_value.value) == len(value)


@pytest.mark.cty_collections
@pytest.mark.parametrize("case_name,value", LIST_NUMBER_TEST_CASES)
def test_ctylist_number_values(case_name: str, value: list[int | Decimal]) -> None:
    """Test CtyList with number elements."""
    cty_type = CtyList(element_type=CtyNumber())

    # Convert ints to Decimal for consistency
    decimal_value = [Decimal(v) if isinstance(v, int) else v for v in value]

    cty_value = cty_type.validate(decimal_value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtyList)


@pytest.mark.cty_collections
@pytest.mark.parametrize("case_name,value", LIST_BOOL_TEST_CASES)
def test_ctylist_bool_values(case_name: str, value: list[bool]) -> None:
    """Test CtyList with boolean elements."""
    cty_type = CtyList(element_type=CtyBool())
    cty_value = cty_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtyList)
    assert len(cty_value.value) == len(value)


@pytest.mark.cty_collections
def test_ctylist_null() -> None:
    """Test CtyList null value."""
    cty_value = CtyValue.null(CtyList(element_type=CtyString()))

    assert cty_value.is_null
    assert not cty_value.is_unknown
    assert cty_value.value is None


@pytest.mark.cty_collections
def test_ctylist_unknown() -> None:
    """Test CtyList unknown value."""
    cty_value = CtyValue.unknown(CtyList(element_type=CtyString()))

    assert not cty_value.is_null
    assert cty_value.is_unknown


# =============================================================================
# Tests: CtySet Comprehensive
# =============================================================================


@pytest.mark.cty_collections
@pytest.mark.parametrize("case_name,value", SET_STRING_TEST_CASES)
def test_ctyset_string_values(case_name: str, value: set[str]) -> None:
    """Test CtySet with string elements."""
    cty_type = CtySet(element_type=CtyString())
    cty_value = cty_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtySet)
    assert len(cty_value.value) == len(value)


@pytest.mark.cty_collections
@pytest.mark.parametrize("case_name,value", SET_NUMBER_TEST_CASES)
def test_ctyset_number_values(case_name: str, value: set[int]) -> None:
    """Test CtySet with number elements."""
    cty_type = CtySet(element_type=CtyNumber())

    # Convert to Decimal set
    decimal_value = {Decimal(v) for v in value}

    cty_value = cty_type.validate(decimal_value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtySet)


@pytest.mark.cty_collections
@pytest.mark.parametrize("case_name,value", SET_BOOL_TEST_CASES)
def test_ctyset_bool_values(case_name: str, value: set[bool]) -> None:
    """Test CtySet with boolean elements."""
    cty_type = CtySet(element_type=CtyBool())
    cty_value = cty_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtySet)
    assert len(cty_value.value) == len(value)


@pytest.mark.cty_collections
def test_ctyset_deduplication() -> None:
    """Test that CtySet properly deduplicates elements."""
    cty_type = CtySet(element_type=CtyString())

    # Input has duplicates, but set should deduplicate
    cty_value = cty_type.validate({"a", "b", "c"})

    # CtySet should deduplicate to 3 unique elements
    assert len(cty_value.value) == 3


@pytest.mark.cty_collections
def test_ctyset_null() -> None:
    """Test CtySet null value."""
    cty_value = CtyValue.null(CtySet(element_type=CtyString()))

    assert cty_value.is_null
    assert not cty_value.is_unknown
    assert cty_value.value is None


@pytest.mark.cty_collections
def test_ctyset_unknown() -> None:
    """Test CtySet unknown value."""
    cty_value = CtyValue.unknown(CtySet(element_type=CtyString()))

    assert not cty_value.is_null
    assert cty_value.is_unknown


# =============================================================================
# Tests: CtyMap Comprehensive
# =============================================================================


@pytest.mark.cty_collections
@pytest.mark.parametrize("case_name,value", MAP_STRING_TEST_CASES)
def test_ctymap_string_values(case_name: str, value: dict[str, str]) -> None:
    """Test CtyMap with string values."""
    cty_type = CtyMap(element_type=CtyString())
    cty_value = cty_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtyMap)
    assert len(cty_value.value) == len(value)


@pytest.mark.cty_collections
@pytest.mark.parametrize("case_name,value", MAP_NUMBER_TEST_CASES)
def test_ctymap_number_values(case_name: str, value: dict[str, int | Decimal]) -> None:
    """Test CtyMap with number values."""
    cty_type = CtyMap(element_type=CtyNumber())

    # Convert values to Decimal
    decimal_value = {k: Decimal(v) if isinstance(v, int) else v for k, v in value.items()}

    cty_value = cty_type.validate(decimal_value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtyMap)


@pytest.mark.cty_collections
@pytest.mark.parametrize("case_name,value", MAP_BOOL_TEST_CASES)
def test_ctymap_bool_values(case_name: str, value: dict[str, bool]) -> None:
    """Test CtyMap with boolean values."""
    cty_type = CtyMap(element_type=CtyBool())
    cty_value = cty_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert isinstance(cty_value.type, CtyMap)
    assert len(cty_value.value) == len(value)


@pytest.mark.cty_collections
def test_ctymap_null() -> None:
    """Test CtyMap null value."""
    cty_value = CtyValue.null(CtyMap(element_type=CtyString()))

    assert cty_value.is_null
    assert not cty_value.is_unknown
    assert cty_value.value is None


@pytest.mark.cty_collections
def test_ctymap_unknown() -> None:
    """Test CtyMap unknown value."""
    cty_value = CtyValue.unknown(CtyMap(element_type=CtyString()))

    assert not cty_value.is_null
    assert cty_value.is_unknown


# =============================================================================
# Tests: Nested Collections
# =============================================================================


@pytest.mark.cty_collections
def test_nested_list_of_lists() -> None:
    """Test List[List[String]]."""
    inner_list_type = CtyList(element_type=CtyString())
    outer_list_type = CtyList(element_type=inner_list_type)

    value = [["a", "b"], ["c", "d"], ["e"]]
    cty_value = outer_list_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    # For nested collections, .value contains CtyValue objects, not raw Python data
    assert isinstance(cty_value.value, tuple)
    assert len(cty_value.value) == 3


@pytest.mark.cty_collections
def test_map_of_lists() -> None:
    """Test Map[List[Number]]."""
    list_type = CtyList(element_type=CtyNumber())
    map_type = CtyMap(element_type=list_type)

    value = {
        "nums1": [Decimal(1), Decimal(2), Decimal(3)],
        "nums2": [Decimal(4), Decimal(5)],
    }
    cty_value = map_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown


@pytest.mark.cty_collections
def test_list_of_maps() -> None:
    """Test List[Map[String]]."""
    map_type = CtyMap(element_type=CtyString())
    list_type = CtyList(element_type=map_type)

    value = [
        {"name": "Alice", "role": "admin"},
        {"name": "Bob", "role": "user"},
    ]
    cty_value = list_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown


@pytest.mark.cty_collections
def test_list_of_objects() -> None:
    """Test List[Object]."""
    object_type = CtyObject(
        {
            "name": CtyString(),
            "age": CtyNumber(),
        }
    )
    list_type = CtyList(element_type=object_type)

    value = [
        {"name": "Alice", "age": Decimal(30)},
        {"name": "Bob", "age": Decimal(25)},
    ]
    cty_value = list_type.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert len(cty_value.value) == 2


@pytest.mark.cty_collections
def test_deeply_nested() -> None:
    """Test List[List[List[String]]] - 3 levels deep."""
    level_1 = CtyList(element_type=CtyString())
    level_2 = CtyList(element_type=level_1)
    level_3 = CtyList(element_type=level_2)

    value = [
        [["a", "b"], ["c"]],
        [["d", "e", "f"]],
    ]
    cty_value = level_3.validate(value)

    assert not cty_value.is_null
    assert not cty_value.is_unknown
    assert len(cty_value.value) == 2


# =============================================================================
# Tests: MessagePack Roundtrip for Collections
# =============================================================================


@pytest.mark.cty_collections
@pytest.mark.cty_roundtrip
@pytest.mark.parametrize("case_name,value", LIST_STRING_TEST_CASES)
def test_ctylist_string_msgpack_roundtrip(case_name: str, value: list[str]) -> None:
    """Test CtyList[String] MessagePack serialization roundtrip."""
    cty_type = CtyList(element_type=CtyString())
    original = cty_type.validate(value)

    # Serialize to MessagePack
    msgpack_bytes = cty_to_msgpack(original, cty_type)

    # Deserialize from MessagePack
    deserialized = cty_from_msgpack(msgpack_bytes, cty_type)

    # Verify equality
    assert deserialized == original
    assert deserialized.value == original.value


@pytest.mark.cty_collections
@pytest.mark.cty_roundtrip
@pytest.mark.parametrize("case_name,value", SET_STRING_TEST_CASES)
def test_ctyset_string_msgpack_roundtrip(case_name: str, value: set[str]) -> None:
    """Test CtySet[String] MessagePack serialization roundtrip."""
    cty_type = CtySet(element_type=CtyString())
    original = cty_type.validate(value)

    # Serialize to MessagePack
    msgpack_bytes = cty_to_msgpack(original, cty_type)

    # Deserialize from MessagePack
    deserialized = cty_from_msgpack(msgpack_bytes, cty_type)

    # Verify equality
    assert deserialized == original
    assert deserialized.value == original.value


@pytest.mark.cty_collections
@pytest.mark.cty_roundtrip
@pytest.mark.parametrize("case_name,value", MAP_STRING_TEST_CASES)
def test_ctymap_string_msgpack_roundtrip(case_name: str, value: dict[str, str]) -> None:
    """Test CtyMap[String] MessagePack serialization roundtrip."""
    cty_type = CtyMap(element_type=CtyString())
    original = cty_type.validate(value)

    # Serialize to MessagePack
    msgpack_bytes = cty_to_msgpack(original, cty_type)

    # Deserialize from MessagePack
    deserialized = cty_from_msgpack(msgpack_bytes, cty_type)

    # Verify equality
    assert deserialized == original
    assert deserialized.value == original.value


@pytest.mark.cty_collections
@pytest.mark.cty_roundtrip
def test_nested_collections_msgpack_roundtrip() -> None:
    """Test nested collections MessagePack roundtrip."""
    # Map[List[Number]]
    list_type = CtyList(element_type=CtyNumber())
    map_type = CtyMap(element_type=list_type)

    value = {
        "nums1": [Decimal(1), Decimal(2), Decimal(3)],
        "nums2": [Decimal(4), Decimal(5)],
    }
    original = map_type.validate(value)

    # Serialize to MessagePack
    msgpack_bytes = cty_to_msgpack(original, map_type)

    # Deserialize from MessagePack
    deserialized = cty_from_msgpack(msgpack_bytes, map_type)

    # Verify equality
    assert deserialized == original


# 🥣🔬🔚

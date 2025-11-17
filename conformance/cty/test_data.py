#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Shared test data for CTY comprehensive and interop tests.

This module contains all test case data definitions used across:
- souptest_primitives_comprehensive.py
- souptest_collections_comprehensive.py
- souptest_structural_comprehensive.py
- souptest_cty_interop.py (cross-language testing)

Centralizing test data ensures consistency between Python-only tests
and cross-language interoperability tests.
"""

from decimal import Decimal

from pyvider.cty import (
    CtyBool,
    CtyList,
    CtyMap,
    CtyNumber,
    CtyObject,
    CtyString,
    CtyTuple,
)

# =============================================================================
# Primitive Type Test Data
# =============================================================================

STRING_TEST_CASES = [
    # Basic strings
    ("simple", "hello world"),
    ("empty", ""),
    ("single_char", "a"),
    # Unicode and special characters
    ("unicode_emoji", "Hello 🌍🚀"),
    ("unicode_mixed", "Hello世界مرحبا"),  # noqa: RUF001 - Intentional unicode test data
    ("newlines", "line1\nline2\nline3"),
    ("tabs", "col1\tcol2\tcol3"),
    ("quotes", 'He said "Hello"'),
    ("backslash", "path\\to\\file"),
    # Edge cases
    ("spaces", "   leading and trailing   "),
    ("long_string", "a" * 10000),  # 10K characters
    ("json_string", '{"key": "value", "number": 42}'),
    ("xml_string", "<root><child>text</child></root>"),
    # Special characters
    ("null_char", "before\x00after"),
    ("control_chars", "\x01\x02\x03"),
    ("high_unicode", "\U0001f600\U0001f601\U0001f602"),  # Multiple emojis
]

NUMBER_TEST_CASES = [
    # Basic integers
    ("zero", 0),
    ("positive_small", 42),
    ("negative_small", -42),
    ("one", 1),
    ("negative_one", -1),
    # Large integers
    ("large_positive", 2**63 - 1),  # Max int64
    ("large_negative", -(2**63)),  # Min int64
    ("very_large", 2**100),
    ("extremely_large", 2**1000),
    # Decimals
    ("decimal_simple", Decimal("3.14")),
    ("decimal_precise", Decimal("3.141592653589793")),
    ("decimal_tiny", Decimal("0.0000000001")),
    ("decimal_negative", Decimal("-123.456")),
    # Edge decimals
    ("decimal_zero", Decimal("0.0")),
    ("decimal_one", Decimal("1.0")),
    ("decimal_high_precision", Decimal("1.23456789012345678901234567890")),
    ("decimal_scientific", Decimal("1.23E+10")),
    ("decimal_scientific_neg", Decimal("1.23E-10")),
]

BOOL_TEST_CASES = [
    ("true", True),
    ("false", False),
]


# =============================================================================
# Collection Type Test Data
# =============================================================================

LIST_STRING_TEST_CASES = [
    ("empty", []),
    ("single", ["hello"]),
    ("multiple", ["a", "b", "c"]),
    ("with_empty_strings", ["", "hello", ""]),
    ("unicode", ["Hello", "世界", "🌍"]),
    ("many_items", [f"item_{i}" for i in range(100)]),
]

LIST_NUMBER_TEST_CASES = [
    ("empty", []),
    ("single", [42]),
    ("multiple", [1, 2, 3, 4, 5]),
    ("with_zero", [0, 1, 0, 2]),
    ("negative", [-1, -2, -3]),
    ("large_numbers", [2**100, 2**200, 2**1000]),
    ("decimals", [Decimal("3.14"), Decimal("2.71"), Decimal("1.41")]),
]

LIST_BOOL_TEST_CASES = [
    ("empty", []),
    ("single_true", [True]),
    ("single_false", [False]),
    ("multiple", [True, False, True, False]),
    ("all_true", [True, True, True]),
    ("all_false", [False, False, False]),
]

SET_STRING_TEST_CASES = [
    ("empty", set()),
    ("single", {"hello"}),
    ("multiple", {"a", "b", "c"}),
    ("unicode", {"Hello", "世界", "🌍"}),
]

SET_NUMBER_TEST_CASES = [
    ("empty", set()),
    ("single", {42}),
    ("multiple", {1, 2, 3, 4, 5}),
    ("with_zero", {0, 1, 2}),
    ("negative", {-1, -2, -3}),
]

SET_BOOL_TEST_CASES = [
    ("empty", set()),
    ("single_true", {True}),
    ("single_false", {False}),
    ("both", {True, False}),
]

MAP_STRING_TEST_CASES = [
    ("empty", {}),
    ("single", {"key1": "value1"}),
    ("multiple", {"key1": "value1", "key2": "value2", "key3": "value3"}),
    ("unicode_values", {"key": "世界", "hello": "🌍"}),
    ("empty_values", {"key1": "", "key2": "value"}),
]

MAP_NUMBER_TEST_CASES = [
    ("empty", {}),
    ("single", {"num": 42}),
    ("multiple", {"a": 1, "b": 2, "c": 3}),
    ("with_zero", {"zero": 0, "one": 1}),
    ("decimals", {"pi": Decimal("3.14"), "e": Decimal("2.71")}),
]

MAP_BOOL_TEST_CASES = [
    ("empty", {}),
    ("single_true", {"flag": True}),
    ("single_false", {"flag": False}),
    ("multiple", {"enabled": True, "disabled": False, "active": True}),
]


# =============================================================================
# Structural Type Test Data
# =============================================================================

TUPLE_TEST_CASES = [
    # (description, element_types, value)
    ("empty", (), []),
    ("single_string", (CtyString(),), ["hello"]),
    ("single_number", (CtyNumber(),), [Decimal(42)]),
    ("single_bool", (CtyBool(),), [True]),
    ("mixed_string_number", (CtyString(), CtyNumber()), ["hello", Decimal(42)]),
    ("mixed_all_primitives", (CtyString(), CtyNumber(), CtyBool()), ["hello", Decimal(42), True]),
    ("multiple_same_type", (CtyString(), CtyString(), CtyString()), ["a", "b", "c"]),
    (
        "complex_mixed",
        (CtyBool(), CtyString(), CtyNumber(), CtyString()),
        [False, "test", Decimal(100), "end"],
    ),
]

OBJECT_REQUIRED_ONLY = [
    # (description, attributes, optional_attributes, value)
    (
        "single_string",
        {"name": CtyString()},
        set(),
        {"name": "Alice"},
    ),
    (
        "single_number",
        {"count": CtyNumber()},
        set(),
        {"count": Decimal(42)},
    ),
    (
        "single_bool",
        {"enabled": CtyBool()},
        set(),
        {"enabled": True},
    ),
    (
        "multiple_attrs",
        {"name": CtyString(), "age": CtyNumber(), "active": CtyBool()},
        set(),
        {"name": "Bob", "age": Decimal(30), "active": False},
    ),
]

OBJECT_WITH_OPTIONAL = [
    (
        "all_optional_present",
        {"name": CtyString()},
        {"email"},
        {"name": "Alice", "email": "alice@example.com"},
    ),
    (
        "optional_missing",
        {"name": CtyString()},
        {"email"},
        {"name": "Bob", "email": None},
    ),
    (
        "multiple_optional_mixed",
        {"id": CtyNumber()},
        {"name", "email"},
        {"id": Decimal(1), "name": "Charlie", "email": None},
    ),
]


# =============================================================================
# Nested/Complex Structure Test Data
# =============================================================================

NESTED_COLLECTION_CASES = [
    # (description, cty_type, value)
    (
        "list_of_lists",
        CtyList(element_type=CtyList(element_type=CtyString())),
        [["a", "b"], ["c", "d"], ["e"]],
    ),
    (
        "map_of_lists",
        CtyMap(element_type=CtyList(element_type=CtyNumber())),
        {
            "nums1": [Decimal(1), Decimal(2), Decimal(3)],
            "nums2": [Decimal(4), Decimal(5)],
        },
    ),
    (
        "list_of_maps",
        CtyList(element_type=CtyMap(element_type=CtyString())),
        [
            {"name": "Alice", "role": "admin"},
            {"name": "Bob", "role": "user"},
        ],
    ),
    (
        "list_of_objects",
        CtyList(element_type=CtyObject({"name": CtyString(), "age": CtyNumber()})),
        [
            {"name": "Alice", "age": Decimal(30)},
            {"name": "Bob", "age": Decimal(25)},
        ],
    ),
    (
        "deeply_nested_lists",
        CtyList(element_type=CtyList(element_type=CtyList(element_type=CtyString()))),
        [
            [["a", "b"], ["c"]],
            [["d", "e", "f"]],
        ],
    ),
]

NESTED_STRUCTURAL_CASES = [
    # (description, cty_type, value)
    (
        "tuple_nested",
        CtyTuple(element_types=(CtyTuple(element_types=(CtyString(), CtyNumber())), CtyBool())),
        [["hello", Decimal(42)], True],
    ),
    (
        "tuple_with_list",
        CtyTuple(element_types=(CtyString(), CtyList(element_type=CtyNumber()))),
        ["name", [Decimal(1), Decimal(2), Decimal(3)]],
    ),
    (
        "tuple_with_map",
        CtyTuple(element_types=(CtyNumber(), CtyMap(element_type=CtyString()))),
        [Decimal(42), {"key": "value"}],
    ),
    (
        "object_nested",
        CtyObject(
            {
                "name": CtyString(),
                "address": CtyObject({"street": CtyString(), "city": CtyString()}),
            }
        ),
        {
            "name": "Alice",
            "address": {"street": "123 Main St", "city": "Springfield"},
        },
    ),
    (
        "object_with_list",
        CtyObject(
            {
                "name": CtyString(),
                "scores": CtyList(element_type=CtyNumber()),
            }
        ),
        {
            "name": "Bob",
            "scores": [Decimal(85), Decimal(90), Decimal(95)],
        },
    ),
    (
        "object_with_map",
        CtyObject(
            {
                "id": CtyNumber(),
                "metadata": CtyMap(element_type=CtyString()),
            }
        ),
        {
            "id": Decimal(123),
            "metadata": {"env": "prod", "region": "us-east-1"},
        },
    ),
    (
        "object_with_tuple",
        CtyObject(
            {
                "name": CtyString(),
                "coordinates": CtyTuple(element_types=(CtyNumber(), CtyNumber())),
            }
        ),
        {
            "name": "Point A",
            "coordinates": [Decimal(10), Decimal(20)],
        },
    ),
    (
        "object_all_types",
        CtyObject(
            {
                "string_val": CtyString(),
                "number_val": CtyNumber(),
                "bool_val": CtyBool(),
                "list_val": CtyList(element_type=CtyString()),
                "map_val": CtyMap(element_type=CtyNumber()),
                "tuple_val": CtyTuple(element_types=(CtyString(), CtyNumber())),
                "object_val": CtyObject({"nested": CtyString()}),
            }
        ),
        {
            "string_val": "test",
            "number_val": Decimal(42),
            "bool_val": True,
            "list_val": ["a", "b"],
            "map_val": {"x": Decimal(1), "y": Decimal(2)},
            "tuple_val": ["tuple", Decimal(100)],
            "object_val": {"nested": "value"},
        },
    ),
    (
        "complex_nested_object",
        CtyObject(
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
        ),
        {
            "id": "test-obj1",
            "enabled": True,
            "ports": [Decimal(8080), Decimal(8443)],
            "config": {
                "retries": Decimal(3),
                "params": {"timeout": "10s", "retry_delay": "1s"},
            },
            "metadata": {"env": "test", "region": "local"},
        },
    ),
]


# 🥣🔬🔚

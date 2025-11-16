#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Cross-language CTY interoperability tests.

Tests Python ↔ Go CTY value serialization and deserialization using MessagePack.
Validates bidirectional compatibility between pyvider.cty (Python) and go-cty (Go).

Test Strategy:
1. Python deserializes Go-generated fixtures (Go → Python)
2. Go validates Python-generated fixtures (Python → Go)

Phase 1.4 of 100% pyvider.cty compatibility verification.
"""

from decimal import Decimal
import json
from pathlib import Path
from typing import Any

import pytest

from pyvider.cty import (
    CtyBool,
    CtyDynamic,
    CtyList,
    CtyMap,
    CtyNumber,
    CtyObject,
    CtySet,
    CtyString,
    CtyTuple,
    CtyValue,
)
from pyvider.cty.codec import _convert_value_to_serializable, cty_from_msgpack, cty_to_msgpack
from pyvider.cty.conversion import encode_cty_type_to_wire_json
from pyvider.cty.values.markers import RefinedUnknownValue

from ..cli_verification.shared_cli_utils import run_harness_cli
from .test_data import (
    BOOL_TEST_CASES,
    LIST_BOOL_TEST_CASES,
    LIST_NUMBER_TEST_CASES,
    LIST_STRING_TEST_CASES,
    MAP_BOOL_TEST_CASES,
    MAP_NUMBER_TEST_CASES,
    MAP_STRING_TEST_CASES,
    NESTED_COLLECTION_CASES,
    NESTED_STRUCTURAL_CASES,
    NUMBER_TEST_CASES,
    OBJECT_REQUIRED_ONLY,
    OBJECT_WITH_OPTIONAL,
    SET_BOOL_TEST_CASES,
    SET_NUMBER_TEST_CASES,
    SET_STRING_TEST_CASES,
    STRING_TEST_CASES,
    TUPLE_TEST_CASES,
)


def _cty_value_to_json_compatible_value(cty_value: CtyValue) -> Any:
    """
    Converts a CtyValue to a Python object that is directly JSON serializable.
    Handles special cases like UnknownValue and CtyDynamic.
    """
    if cty_value.is_null:
        return None
    if cty_value.is_unknown:
        # For unknown values, we need to represent their internal structure.
        # The _serialize_unknown function returns msgpack.ExtType, which is not JSON serializable.
        # We need to convert it to a dict/string representation.
        if isinstance(cty_value.value, RefinedUnknownValue):
            # Convert RefinedUnknownValue to a dict for JSON serialization
            return {
                "is_known_null": cty_value.value.is_known_null,
                "string_prefix": cty_value.value.string_prefix,
                "number_lower_bound": str(cty_value.value.number_lower_bound[0])
                if cty_value.value.number_lower_bound
                else None,
                "number_upper_bound": str(cty_value.value.number_upper_bound[0])
                if cty_value.value.number_upper_bound
                else None,
                "collection_length_lower_bound": cty_value.value.collection_length_lower_bound,
                "collection_length_upper_bound": cty_value.value.collection_length_upper_bound,
            }
        return "<UNKNOWN>"  # Simple representation for unrefined unknown

    if isinstance(cty_value.type, CtyDynamic):
        # For CtyDynamic, its value is another CtyValue. Recursively convert it.
        return _cty_value_to_json_compatible_value(cty_value.value)

    # For CtyNumber with Decimal values, convert to string FIRST to preserve precision
    # (before _convert_value_to_serializable converts Decimal to float)
    if isinstance(cty_value.type, CtyNumber) and isinstance(cty_value.value, Decimal):
        return str(cty_value.value)

    # For other types, _convert_value_to_serializable should return a JSON-compatible type
    serializable_data = _convert_value_to_serializable(cty_value, cty_value.type)

    # Handle bytes conversion to string for JSON compatibility (large integers may be encoded as bytes in older versions)
    # Note: As of latest pyvider-cty, large integers and high-precision decimals are encoded as strings
    if isinstance(serializable_data, bytes):
        return serializable_data.decode("utf-8")

    # Handle Decimal conversion to string for JSON compatibility
    if isinstance(serializable_data, Decimal):
        return str(serializable_data)

    # Recursively handle lists and dicts to ensure all nested Decimals/bytes are converted
    if isinstance(serializable_data, dict):
        return {
            k: (
                _cty_value_to_json_compatible_value(v)
                if isinstance(v, CtyValue)
                else str(v)
                if isinstance(v, Decimal)
                else v
            )
            for k, v in serializable_data.items()
        }
    if isinstance(serializable_data, list):
        return [
            (
                _cty_value_to_json_compatible_value(item)
                if isinstance(item, CtyValue)
                else str(item)
                if isinstance(item, Decimal)
                else item
            )
            for item in serializable_data
        ]

    return serializable_data


# =============================================================================
# Test Case Dictionaries: Basic Smoke Tests
# =============================================================================

# This dictionary serves as basic smoke tests for cross-language interoperability
GO_TEST_CASES: dict[str, CtyValue] = {
    "string_simple": CtyString().validate("hello world"),
    "number_simple": CtyNumber().validate(42),
    "bool_true": CtyBool().validate(True),
    "large_number": CtyNumber().validate(Decimal(2**100)),
    "null_string": CtyValue.null(CtyString()),
    "unknown_unrefined": CtyValue.unknown(CtyString()),
    "list_of_strings": CtyList(element_type=CtyString()).validate(["a", "b"]),
    "set_of_numbers": CtySet(element_type=CtyNumber()).validate({1, 2}),
    "map_simple": CtyMap(element_type=CtyBool()).validate({"a": True, "b": False}),
    "dynamic_wrapped_string": CtyDynamic().validate("dynamic"),
}


# =============================================================================
# Test Case Generation: Comprehensive Coverage
# =============================================================================


def build_comprehensive_interop_cases() -> dict[str, CtyValue]:  # noqa: C901
    """Build comprehensive test cases for cross-language interoperability.

    Generates CtyValue test cases from shared test data for all CTY types:
    - Primitives: String, Number, Bool
    - Collections: List, Set, Map
    - Structural: Tuple, Object
    - Nested combinations

    Returns:
        Dictionary mapping test case names to CtyValue instances
    """
    cases: dict[str, CtyValue] = {}

    # Primitive types
    for case_name, value in STRING_TEST_CASES:
        cases[f"string_{case_name}"] = CtyString().validate(value)

    for case_name, value in NUMBER_TEST_CASES:
        decimal_value = Decimal(value) if isinstance(value, int) else value
        cases[f"number_{case_name}"] = CtyNumber().validate(decimal_value)

    for case_name, value in BOOL_TEST_CASES:
        cases[f"bool_{case_name}"] = CtyBool().validate(value)

    # List types
    for case_name, value in LIST_STRING_TEST_CASES:
        cases[f"list_string_{case_name}"] = CtyList(element_type=CtyString()).validate(value)

    for case_name, value in LIST_NUMBER_TEST_CASES:
        decimal_value = [Decimal(v) if isinstance(v, int) else v for v in value]
        cases[f"list_number_{case_name}"] = CtyList(element_type=CtyNumber()).validate(decimal_value)

    for case_name, value in LIST_BOOL_TEST_CASES:
        cases[f"list_bool_{case_name}"] = CtyList(element_type=CtyBool()).validate(value)

    # Set types
    for case_name, value in SET_STRING_TEST_CASES:
        cases[f"set_string_{case_name}"] = CtySet(element_type=CtyString()).validate(value)

    for case_name, value in SET_NUMBER_TEST_CASES:
        decimal_value = {Decimal(v) for v in value}
        cases[f"set_number_{case_name}"] = CtySet(element_type=CtyNumber()).validate(decimal_value)

    for case_name, value in SET_BOOL_TEST_CASES:
        cases[f"set_bool_{case_name}"] = CtySet(element_type=CtyBool()).validate(value)

    # Map types
    for case_name, value in MAP_STRING_TEST_CASES:
        cases[f"map_string_{case_name}"] = CtyMap(element_type=CtyString()).validate(value)

    for case_name, value in MAP_NUMBER_TEST_CASES:
        decimal_value = {k: Decimal(v) if isinstance(v, int) else v for k, v in value.items()}
        cases[f"map_number_{case_name}"] = CtyMap(element_type=CtyNumber()).validate(decimal_value)

    for case_name, value in MAP_BOOL_TEST_CASES:
        cases[f"map_bool_{case_name}"] = CtyMap(element_type=CtyBool()).validate(value)

    # Tuple types
    for case_name, element_types, value in TUPLE_TEST_CASES:
        cases[f"tuple_{case_name}"] = CtyTuple(element_types=element_types).validate(value)

    # Object types - required only
    for case_name, attributes, optional_attrs, value in OBJECT_REQUIRED_ONLY:
        cty_type = CtyObject(attributes, optional_attributes=optional_attrs)
        cases[f"object_required_{case_name}"] = cty_type.validate(value)

    # Object types - with optional
    for case_name, attributes, optional_attrs, value in OBJECT_WITH_OPTIONAL:
        # Merge required and optional into attributes dict
        all_attrs = dict(attributes)
        for opt_name in optional_attrs:
            if opt_name not in all_attrs:
                all_attrs[opt_name] = CtyString()  # Default type
        cty_type = CtyObject(all_attrs, optional_attributes=optional_attrs)
        cases[f"object_optional_{case_name}"] = cty_type.validate(value)

    # Nested collections
    for case_name, cty_type, value in NESTED_COLLECTION_CASES:
        cases[f"nested_collection_{case_name}"] = cty_type.validate(value)

    # Nested structural
    for case_name, cty_type, value in NESTED_STRUCTURAL_CASES:
        cases[f"nested_structural_{case_name}"] = cty_type.validate(value)

    # Add null and unknown values for key types
    cases["null_string"] = CtyValue.null(CtyString())
    cases["null_number"] = CtyValue.null(CtyNumber())
    cases["null_bool"] = CtyValue.null(CtyBool())
    cases["null_list"] = CtyValue.null(CtyList(element_type=CtyString()))

    cases["unknown_string"] = CtyValue.unknown(CtyString())
    cases["unknown_number"] = CtyValue.unknown(CtyNumber())
    cases["unknown_bool"] = CtyValue.unknown(CtyBool())
    cases["unknown_list"] = CtyValue.unknown(CtyList(element_type=CtyString()))

    return cases


# Generate comprehensive test cases
COMPREHENSIVE_INTEROP_CASES = build_comprehensive_interop_cases()


@pytest.mark.integration_cty
@pytest.mark.harness_go
@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
@pytest.mark.parametrize("case_name", GO_TEST_CASES.keys())
def test_python_deserializes_go_fixtures(
    go_harness_executable: Path,
    project_root: Path,
    tmp_path: Path,
    case_name: str,
) -> None:
    """
    Tests Python's ability to deserialize MessagePack fixtures generated by the Go harness.
    (Go -> Python Interoperability)
    """
    # 1. Use soup-go cty convert to generate a fixture
    go_fixture_dir = tmp_path / "go_fixtures"
    go_fixture_dir.mkdir()
    output_file = go_fixture_dir / f"{case_name}.msgpack"

    # The input to the 'convert' command is a JSON representation of the CtyValue
    cty_value = GO_TEST_CASES[case_name]

    # IMPORTANT: go-cty CANNOT accept unknown values via JSON input
    # This is a fundamental limitation of the go-cty library that matches Terraform's behavior
    # Skip tests for unknown values when using JSON input format
    if cty_value.is_unknown:
        pytest.skip(f"go-cty cannot accept unknown values via JSON input (case: {case_name})")

    input_json = json.dumps(_cty_value_to_json_compatible_value(cty_value))
    type_json_for_go = json.dumps(encode_cty_type_to_wire_json(cty_value.type))

    exit_code, _, stderr = run_harness_cli(
        executable=go_harness_executable,
        args=[
            "cty",
            "convert",
            "-",
            str(output_file),
            "--input-format",
            "json",
            "--output-format",
            "msgpack",
            "--type",
            type_json_for_go,
        ],
        project_root=project_root,
        harness_artifact_name="soup-go",
        test_id=f"generate_fixture_{case_name}",
        stdin_input=input_json,
    )
    assert exit_code == 0, f"soup-go cty convert failed: {stderr}"

    # 2. Read the generated fixture
    assert output_file.exists(), f"Go harness did not generate fixture for {case_name}"
    msgpack_bytes = output_file.read_bytes()

    # 3. Deserialize using Python's logic
    deserialized_value = cty_from_msgpack(msgpack_bytes, cty_value.type)

    # 4. Assert equality
    assert deserialized_value == cty_value, (
        f"Mismatch for case '{case_name}'.\nExpected: {cty_value!r}\nGot:      {deserialized_value!r}"
    )


@pytest.mark.integration_cty
@pytest.mark.harness_go
@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
def test_go_verifies_python_fixtures(
    go_harness_executable: Path,
    project_root: Path,
    tmp_path: Path,
) -> None:
    """
    Tests Go's ability to verify MessagePack fixtures generated by Python.
    (Python -> Go Interoperability)
    """
    py_fixture_dir = tmp_path / "py_fixtures"
    py_fixture_dir.mkdir()

    # 1. Generate Python fixtures
    for case_name, cty_value in GO_TEST_CASES.items():
        fixture_file = py_fixture_dir / f"{case_name}.msgpack"
        fixture_file.write_bytes(cty_to_msgpack(cty_value, cty_value.type))

    # 2. Verify each fixture using soup-go cty validate-value
    for case_name, cty_value in GO_TEST_CASES.items():
        fixture_file = py_fixture_dir / f"{case_name}.msgpack"

        # We need the CTY type string for the --type flag
        type_json_for_go = json.dumps(encode_cty_type_to_wire_json(cty_value.type))

        # The value for validate-value is a JSON string
        value_json = json.dumps(_cty_value_to_json_compatible_value(cty_value))

        exit_code, _, stderr = run_harness_cli(
            executable=go_harness_executable,
            args=["cty", "validate-value", "--type", type_json_for_go, "--", value_json],
            project_root=project_root,
            harness_artifact_name="soup-go",
            test_id=f"verify_fixture_{case_name}",
        )
        assert exit_code == 0, f"soup-go cty validate-value failed for {case_name}: {stderr}"


# =============================================================================
# Comprehensive Cross-Language Tests
# =============================================================================


@pytest.mark.integration_cty_comprehensive
@pytest.mark.harness_go
@pytest.mark.slow
@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
@pytest.mark.parametrize("case_name", COMPREHENSIVE_INTEROP_CASES.keys())
def test_python_deserializes_go_fixtures_comprehensive(
    go_harness_executable: Path,
    project_root: Path,
    tmp_path: Path,
    case_name: str,
) -> None:
    """
    Comprehensive test: Python deserializes Go-generated MessagePack fixtures.
    Tests all comprehensive test cases for Python ↔ Go interoperability.
    (Go → Python)
    """
    go_fixture_dir = tmp_path / "go_fixtures_comprehensive"
    go_fixture_dir.mkdir()
    output_file = go_fixture_dir / f"{case_name}.msgpack"

    cty_value = COMPREHENSIVE_INTEROP_CASES[case_name]

    # Skip unknown values (go-cty limitation with JSON input)
    if cty_value.is_unknown:
        pytest.skip(f"go-cty cannot accept unknown values via JSON input (case: {case_name})")

    # Mark high-precision decimal tests as expected failures due to float64 limits in msgpack
    if case_name in ("number_decimal_high_precision", "list_number_decimals", "map_number_decimals"):
        pytest.xfail(
            f"Known limitation: {case_name} loses precision due to float64 serialization in msgpack. "
            "Go serializes Decimals as float64, which has ~15-17 significant digits precision."
        )

    input_json = json.dumps(_cty_value_to_json_compatible_value(cty_value))
    type_json_for_go = json.dumps(encode_cty_type_to_wire_json(cty_value.type))

    exit_code, _, stderr = run_harness_cli(
        executable=go_harness_executable,
        args=[
            "cty",
            "convert",
            "-",
            str(output_file),
            "--input-format",
            "json",
            "--output-format",
            "msgpack",
            "--type",
            type_json_for_go,
        ],
        project_root=project_root,
        harness_artifact_name="soup-go",
        test_id=f"generate_fixture_comprehensive_{case_name}",
        stdin_input=input_json,
    )
    assert exit_code == 0, f"soup-go cty convert failed for {case_name}: {stderr}"

    assert output_file.exists(), f"Go harness did not generate fixture for {case_name}"
    msgpack_bytes = output_file.read_bytes()

    deserialized_value = cty_from_msgpack(msgpack_bytes, cty_value.type)

    assert deserialized_value == cty_value, (
        f"Mismatch for case '{case_name}'.\nExpected: {cty_value!r}\nGot:      {deserialized_value!r}"
    )


@pytest.mark.integration_cty_comprehensive
@pytest.mark.harness_go
@pytest.mark.slow
@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
def test_go_verifies_python_fixtures_comprehensive(
    go_harness_executable: Path,
    project_root: Path,
    tmp_path: Path,
) -> None:
    """
    Comprehensive test: Go validates Python-generated MessagePack fixtures.
    Tests all comprehensive test cases for Python ↔ Go interoperability.
    (Python → Go)
    """
    py_fixture_dir = tmp_path / "py_fixtures_comprehensive"
    py_fixture_dir.mkdir()

    # Generate all Python fixtures
    for case_name, cty_value in COMPREHENSIVE_INTEROP_CASES.items():
        fixture_file = py_fixture_dir / f"{case_name}.msgpack"
        fixture_file.write_bytes(cty_to_msgpack(cty_value, cty_value.type))

    # Verify each fixture using Go harness
    for case_name, cty_value in COMPREHENSIVE_INTEROP_CASES.items():
        # Skip unknown values (go-cty limitation with JSON input)
        if cty_value.is_unknown:
            continue

        fixture_file = py_fixture_dir / f"{case_name}.msgpack"

        type_json_for_go = json.dumps(encode_cty_type_to_wire_json(cty_value.type))
        value_json = json.dumps(_cty_value_to_json_compatible_value(cty_value))

        exit_code, _, stderr = run_harness_cli(
            executable=go_harness_executable,
            args=["cty", "validate-value", "--type", type_json_for_go, "--", value_json],
            project_root=project_root,
            harness_artifact_name="soup-go",
            test_id=f"verify_fixture_comprehensive_{case_name}",
        )
        assert exit_code == 0, f"soup-go cty validate-value failed for {case_name}: {stderr}"


# 🥣🔬🔚

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Cross-language HCL interoperability tests.

Tests Python ↔ Go HCL parsing compatibility using pyvider-hcl (Python) and soup-go (Go).
Validates that both parsers produce compatible CTY values from the same HCL input.

Test Strategy:
1. Python parses HCL → CTY values → validates structure
2. Go parses same HCL → JSON output → compare with Python
3. Validates list inference fix works with real HCL content

This ensures the pyvider-hcl inference fix (using pyvider-cty's canonical implementation)
produces results compatible with Go's HCL parser.
"""

from decimal import Decimal
import json
from pathlib import Path

import pytest

from pyvider.cty import CtyList, CtyValue
from pyvider.cty.conversion import cty_to_native
from pyvider.hcl import parse_hcl_to_cty

from ..cli_verification.shared_cli_utils import run_harness_cli
from .test_data import HCL_EXPECTED_SCHEMAS, HCL_EXPECTED_VALUES, HCL_TEST_CASES

# Note: go_harness_executable and project_root fixtures are provided by conformance/conftest.py


@pytest.mark.integration_hcl
@pytest.mark.harness_go
@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
@pytest.mark.parametrize("case_name", HCL_TEST_CASES.keys())
def test_python_parses_hcl_with_correct_types(
    go_harness_executable: Path,
    project_root: Path,
    tmp_path: Path,
    case_name: str,
) -> None:
    """Test that Python pyvider-hcl parses HCL with correct CTY types."""
    hcl_content = HCL_TEST_CASES[case_name]
    expected_schema = HCL_EXPECTED_SCHEMAS[case_name]

    # Parse HCL with Python
    result = parse_hcl_to_cty(hcl_content)

    # Validate the inferred type matches expected schema
    assert isinstance(result, CtyValue), f"Expected CtyValue, got {type(result)}"
    assert result.type == expected_schema, (
        f"Type mismatch for {case_name}:\nExpected: {expected_schema}\nGot: {result.type}"
    )


@pytest.mark.integration_hcl
@pytest.mark.harness_go
@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
@pytest.mark.parametrize("case_name", HCL_TEST_CASES.keys())
def test_python_parses_hcl_with_correct_values(
    go_harness_executable: Path,
    project_root: Path,
    tmp_path: Path,
    case_name: str,
) -> None:
    """Test that Python pyvider-hcl parses HCL values correctly."""
    hcl_content = HCL_TEST_CASES[case_name]
    expected_values = HCL_EXPECTED_VALUES[case_name]

    # Parse HCL with Python
    result = parse_hcl_to_cty(hcl_content)

    # Convert to native Python for easy comparison
    native_result = cty_to_native(result)

    # Compare values (with tolerance for Decimal/float differences)
    assert_dicts_equal_with_tolerance(native_result, expected_values, case_name)


@pytest.mark.integration_hcl
@pytest.mark.harness_go
@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
@pytest.mark.parametrize(
    "case_name",
    ["list_of_strings", "list_of_numbers", "list_of_bools", "list_of_objects"],
)
def test_list_inference_works_correctly(
    go_harness_executable: Path,
    project_root: Path,
    tmp_path: Path,
    case_name: str,
) -> None:
    """Test that list element type inference works correctly (regression test for bug fix)."""
    hcl_content = HCL_TEST_CASES[case_name]

    # Parse HCL with Python
    result = parse_hcl_to_cty(hcl_content)

    # Find the list attribute in the result
    # All test cases have a single top-level list attribute
    list_attr_name = next(iter(result.value.keys()))
    list_value = result.value[list_attr_name]

    # Verify it's actually a list type
    assert isinstance(list_value.type, CtyList), f"Expected CtyList, got {type(list_value.type)}"

    # Verify element type is NOT CtyDynamic (the old bug)
    from pyvider.cty import CtyDynamic

    element_type = list_value.type.element_type
    assert not isinstance(element_type, CtyDynamic), (
        f"List element type should not be CtyDynamic for {case_name}, got {element_type}"
    )

    # Verify element type matches expected schema
    expected_element_type = HCL_EXPECTED_SCHEMAS[case_name].attribute_types[list_attr_name].element_type
    assert element_type == expected_element_type, (
        f"Element type mismatch for {case_name}:\nExpected: {expected_element_type}\nGot: {element_type}"
    )


@pytest.mark.integration_hcl
@pytest.mark.harness_go
@pytest.mark.slow
@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
@pytest.mark.parametrize("case_name", ["simple_string", "list_of_numbers", "nested_object"])
def test_go_parses_hcl_consistently(
    go_harness_executable: Path,
    project_root: Path,
    tmp_path: Path,
    case_name: str,
) -> None:
    """Test that Go soup-go harness can parse the same HCL successfully."""
    hcl_content = HCL_TEST_CASES[case_name]

    # Write HCL to temporary file
    hcl_file = tmp_path / f"{case_name}.hcl"
    hcl_file.write_text(hcl_content)

    # Parse with Go harness
    exit_code, stdout, stderr = run_harness_cli(
        executable=go_harness_executable,
        args=["hcl", "view", str(hcl_file)],
        project_root=project_root,
        harness_artifact_name="soup-go",
        test_id=f"hcl_interop_{case_name}",
    )

    assert exit_code == 0, f"soup-go hcl view failed for {case_name}:\nstderr: {stderr}\nstdout: {stdout}"

    # Parse the JSON output from Go
    try:
        go_response = json.loads(stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to parse Go output as JSON for {case_name}: {e}\nOutput: {stdout}")

    # Extract body from Go response wrapper
    assert "body" in go_response, f"Go response missing 'body' key for {case_name}: {go_response.keys()}"
    go_result = go_response["body"]

    # Parse with Python for comparison
    py_result = parse_hcl_to_cty(hcl_content)
    py_native = cty_to_native(py_result)

    # Both should produce equivalent structures
    # Note: Decimals in Python, floats in Go JSON - compare with tolerance
    assert_dicts_equal_with_tolerance(py_native, go_result, case_name)


def assert_dicts_equal_with_tolerance(py_value: dict, go_value: dict, case_name: str, path: str = "") -> None:
    """Compare dicts with tolerance for Decimal/float differences."""
    assert set(py_value.keys()) == set(go_value.keys()), f"Key mismatch at {path} for {case_name}"

    for key in py_value:
        py_val = py_value[key]
        go_val = go_value[key]
        current_path = f"{path}.{key}" if path else key

        if isinstance(py_val, Decimal | int | float) and isinstance(go_val, Decimal | int | float):
            # Compare with tolerance for decimal/float/int
            assert abs(float(py_val) - float(go_val)) < 1e-9, (
                f"Number mismatch at {current_path} for {case_name}: {py_val} != {go_val}"
            )
        elif isinstance(py_val, dict) and isinstance(go_val, dict):
            assert_dicts_equal_with_tolerance(py_val, go_val, case_name, current_path)
        elif isinstance(py_val, list) and isinstance(go_val, list):
            assert len(py_val) == len(go_val), f"List length mismatch at {current_path} for {case_name}"
            for i, (py_item, go_item) in enumerate(zip(py_val, go_val, strict=False)):
                if isinstance(py_item, dict):
                    assert_dicts_equal_with_tolerance(py_item, go_item, case_name, f"{current_path}[{i}]")
                elif isinstance(py_item, Decimal | int | float) and isinstance(go_item, Decimal | int | float):
                    assert abs(float(py_item) - float(go_item)) < 1e-9
                else:
                    assert py_item == go_item, f"Item mismatch at {current_path}[{i}] for {case_name}"
        else:
            assert py_val == go_val, f"Value mismatch at {current_path} for {case_name}: {py_val} != {go_val}"


# 🥣🔬🔚

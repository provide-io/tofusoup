#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import importlib.util
from pathlib import Path
import sys

from _pytest.config import Config
from _pytest.monkeypatch import MonkeyPatch
from _pytest.nodes import Item
from provide.testkit import (
    reset_foundation_setup_for_testing,
)
import pytest


def pytest_configure(config: Config) -> None:
    """Register custom marks."""
    config.addinivalue_line("markers", "tdd: marks tests as TDD (test-driven development)")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "integration_cty: requires CTY integration (pyvider-cty)")
    config.addinivalue_line("markers", "integration_hcl: requires HCL integration (pyvider-hcl + pyvider-cty)")
    config.addinivalue_line("markers", "integration_rpc: requires RPC integration (pyvider-rpcplugin)")
    config.addinivalue_line("markers", "harness_go: requires Go harness")
    config.addinivalue_line("markers", "harness_python: requires Python harness")
    config.addinivalue_line("markers", "requires_textual: marks tests that require Textual app context")
    config.addinivalue_line("markers", "skip_in_ci: marks tests to skip in CI environments")


@pytest.fixture(scope="session", autouse=True)
def add_sibling_source_to_path(request: pytest.FixtureRequest) -> None:
    """
    A session-scoped autouse fixture to dynamically add sibling 'pyvider'
    source directories to the Python path. This is crucial for ensuring
    that tests can import from pyvider.cty, pyvider.hcl, etc., when
    running in environments where they are not installed as editable packages.
    """
    project_root = request.config.rootpath
    # Assuming a standard monorepo layout where pyvider-cty, pyvider-hcl, etc.,
    # are siblings to the tofusoup directory.
    monorepo_root = project_root.parent

    sibling_projects = [
        "pyvider-cty",
        "pyvider-hcl",
        "pyvider",
    ]

    for project in sibling_projects:
        src_path = monorepo_root / project / "src"
        if src_path.is_dir() and str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))


@pytest.fixture(autouse=True)
def skip_integration_if_missing(request: Item) -> None:
    """Skip tests if optional dependencies are missing."""
    marker_checks = {
        "integration_cty": ("pyvider.cty", "cty"),
        "integration_hcl": ("pyvider.hcl", "hcl"),
        "integration_rpc": ("pyvider.rpcplugin", "rpc"),
    }

    for marker_name, (module_name, package_name) in marker_checks.items():
        if request.node.get_closest_marker(marker_name) and importlib.util.find_spec(module_name) is None:
            pytest.skip(
                f"Test requires '{package_name}' integration. "
                f"Install with: pip install tofusoup[{package_name}]"
            )


@pytest.fixture(autouse=True)
def disable_textual_ui_in_tests(monkeypatch: MonkeyPatch) -> None:
    """
    Disable Textual UI features during testing to avoid NoActiveAppError.
    This fixture runs automatically for all tests.
    """
    # Set environment variable to disable any Textual UI features during testing
    monkeypatch.setenv("TOFUSOUP_DISABLE_UI", "1")
    monkeypatch.setenv("TEXTUAL_LOG", "none")


@pytest.fixture(autouse=True)
def reset_foundation_for_tests() -> None:
    """Reset Foundation state between tests for proper isolation."""
    yield
    reset_foundation_setup_for_testing()


@pytest.fixture(scope="session")
def go_soup_harness_path() -> Path:
    """
    Provides the path to the 'soup-go' harness executable.
    """
    harness_executable = Path("src/tofusoup/harness/go/bin/soup-go")
    if not harness_executable.exists():
        pytest.skip(
            f"Go (soup-go) harness executable not found at {harness_executable}, skipping cross-language tests. "
            f"Ensure it has been built (e.g., via 'soup harness build soup-go')."
        )
    return harness_executable


# 🥣🔬🔚

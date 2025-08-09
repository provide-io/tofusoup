import pytest
from pathlib import Path
import sys
import os
from unittest.mock import patch

def pytest_configure(config):
    """Register custom marks."""
    config.addinivalue_line(
        "markers", "tdd: marks tests as TDD (test-driven development)"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "requires_textual: marks tests that require Textual app context"
    )
    config.addinivalue_line(
        "markers", "skip_in_ci: marks tests to skip in CI environments"
    )

@pytest.fixture(scope="session", autouse=True)
def add_sibling_source_to_path(request):
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
def disable_textual_ui_in_tests(monkeypatch):
    """
    Disable Textual UI features during testing to avoid NoActiveAppError.
    This fixture runs automatically for all tests.
    """
    # Set environment variable to disable any Textual UI features during testing
    monkeypatch.setenv("TOFUSOUP_DISABLE_UI", "1")
    monkeypatch.setenv("TEXTUAL_LOG", "none")

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


# 🍲🥄🧪🪄

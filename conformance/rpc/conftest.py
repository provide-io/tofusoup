import pathlib

import pytest

from tofusoup.harness.logic import ensure_go_harness_build


@pytest.fixture(scope="session")
def project_root(request) -> pathlib.Path:
    """Provides the project root directory."""
    return request.config.rootpath


@pytest.fixture(scope="session")
def loaded_tofusoup_config() -> dict:
    """Provides a default empty config for tests."""
    # In a real scenario, this could load a test-specific soup.toml
    return {}


@pytest.fixture(scope="session")
def go_harness_executable(project_root: pathlib.Path, loaded_tofusoup_config: dict) -> pathlib.Path:
    """
    Builds the unified 'soup-go' harness once per session and returns its path.
    This is the single source of truth for the Go harness in all conformance tests.
    """
    try:
        executable_path = ensure_go_harness_build(
            "soup-go", project_root, loaded_tofusoup_config, force_rebuild=True
        )
        if not executable_path.exists():
            pytest.fail(f"Go harness 'soup-go' failed to build at {executable_path}", pytrace=False)
        return executable_path
    except Exception as e:
        pytest.fail(f"Failed to build 'soup-go' harness: {e}", pytrace=False)


@pytest.fixture(scope="session")
def test_artifacts_dir(tmp_path_factory) -> pathlib.Path:
    """
    Creates a session-wide directory for all RPC test artifacts.

    All test outputs (proof manifests, KV storage files, server logs) will be
    written to subdirectories within this directory, organized by test name.

    Returns:
        Path to the test artifacts directory (cleaned up automatically after session)
    """
    artifacts_dir = tmp_path_factory.mktemp("rpc_matrix_proof")
    return artifacts_dir


# Add other shared RPC fixtures here if needed in the future.


# 🍲🥄🧪🪄

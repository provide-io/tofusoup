#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Pytest fixtures for RPC conformance tests.

Provides session-scoped fixtures for:
- Go harness building and path resolution
- Test artifact directory management
- Project root and configuration loading
"""

import pathlib

import pytest

from tofusoup.harness.logic import ensure_go_harness_build


@pytest.fixture(scope="session")
def project_root(request: pytest.FixtureRequest) -> pathlib.Path:
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
def test_artifacts_dir(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """
    Creates a session-wide directory for all RPC test artifacts.

    All test outputs (proof manifests, KV storage files, server logs) will be
    written to subdirectories within this directory, organized by test name.

    Returns:
        Path to the test artifacts directory (cleaned up automatically after session)
    """
    artifacts_dir = tmp_path_factory.mktemp("rpc_matrix_proof")
    return artifacts_dir


def _extract_lang_from_parametrize_markers(item: pytest.Item) -> tuple[str | None, str | None]:
    client_lang = None
    server_lang = None

    for marker in item.iter_markers("parametrize"):
        if marker.args and len(marker.args) > 0:
            param_name = marker.args[0]
            param_values = marker.args[1] if len(marker.args) > 1 else []

            if isinstance(param_name, str) and param_name == "client_lang":
                if isinstance(param_values, (list, tuple)):
                    for value in param_values:
                        if str(value) in item.nodeid:
                            client_lang = str(value)
                            break
            elif (
                isinstance(param_name, str)
                and param_name == "server_lang"
                and isinstance(param_values, (list, tuple))
            ):
                for value in param_values:
                    if str(value) in item.nodeid:
                        server_lang = str(value)
                        break
    return client_lang, server_lang


def _extract_lang_from_callspec_params(item: pytest.Item) -> tuple[str | None, str | None]:
    client_lang = None
    server_lang = None
    if hasattr(item, "callspec") and hasattr(item.callspec, "params"):
        params = item.callspec.params
        if "client_lang" in params:
            client_lang = params["client_lang"]
        if "server_lang" in params:
            server_lang = params["server_lang"]
        if "language" in params:
            lang = str(params["language"])
            if "python" in lang and "go" in lang:
                client_lang = "python"
                server_lang = "go"
    return client_lang, server_lang


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Hook to skip unsupported Python client → Go server combinations early.

    This is a known limitation of pyvider-rpcplugin - Python clients cannot
    connect to Go servers. We skip these tests immediately rather than letting
    them timeout after 30 seconds.
    """
    client_lang, server_lang = _extract_lang_from_parametrize_markers(item)

    # If not found in markers, try callspec params
    if client_lang is None or server_lang is None:
        cs_client_lang, cs_server_lang = _extract_lang_from_callspec_params(item)
        client_lang = client_lang or cs_client_lang
        server_lang = server_lang or cs_server_lang

    # Skip Python client → Go server combinations
    if client_lang == "python" and server_lang == "go":
        pytest.skip("Python client → Go server is not supported (pyvider-rpcplugin limitation)")

    # Also check test name for explicit combinations
    if "python_to_go" in item.nodeid or "pyclient_goserver" in item.nodeid:
        pytest.skip("Python client → Go server is not supported (pyvider-rpcplugin limitation)")


# Add other shared RPC fixtures here if needed in the future.

# 🥣🔬🔚

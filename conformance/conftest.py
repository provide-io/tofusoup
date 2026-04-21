#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Common conftest for tests under 'tofusoup/conformance'.
Provides shared fixtures and test collection modifications."""

import os
from pathlib import Path
import shutil

import pytest

from tofusoup.common.config import load_tofusoup_config
from tofusoup.harness.logic import GO_HARNESS_CONFIG, TofuSoupError, ensure_go_harness_build


@pytest.fixture(scope="session")
def project_root() -> Path:
    """
    Dynamically determine the project root directory by finding pyproject.toml.
    This is robust and environment-agnostic.
    """
    current_path = Path(__file__).resolve()
    while current_path != current_path.parent:
        if (current_path / "pyproject.toml").exists():
            return current_path
        current_path = current_path.parent
    raise FileNotFoundError("Could not find project root containing 'pyproject.toml'.")


@pytest.fixture(scope="session")
def loaded_tofusoup_config(project_root: Path) -> dict:
    """Loads the TofuSoup configuration from soup.toml."""
    return load_tofusoup_config(project_root=project_root, explicit_config_file=None)


@pytest.fixture(scope="session")
def go_harness_executable(
    request: pytest.FixtureRequest, project_root: Path, loaded_tofusoup_config: dict
) -> Path:
    """
    A generic, parameterized fixture to build and provide any Go harness.
    Usage: @pytest.mark.parametrize("go_harness_executable", ["go-cty"], indirect=True)
    """
    harness_key = request.param
    if harness_key not in GO_HARNESS_CONFIG:
        pytest.fail(f"Harness key '{harness_key}' not found in GO_HARNESS_CONFIG.")
    try:
        # THE FIX: Removed the incorrect 'output_base_dir' keyword argument.
        executable_path = ensure_go_harness_build(
            harness_name=harness_key,
            project_root=project_root,
            loaded_config=loaded_tofusoup_config,
            force_rebuild=True,
        )
        if not executable_path.exists() or not os.access(executable_path, os.X_OK):
            pytest.fail(
                f"Go harness executable '{harness_key}' missing or not executable at: {executable_path}"
            )
        return executable_path
    except TofuSoupError as e:
        pytest.fail(f"Failed to ensure Go harness '{harness_key}' was built: {e}")
    # This fallback should not be reached.
    raise RuntimeError(f"Fixture setup for Go harness '{harness_key}' failed unexpectedly.")


# --- Certificate Fixtures (remain unchanged) ---
@pytest.fixture(scope="session", autouse=True)
def _ensure_openssl_available_if_needed_for_anything_else() -> None:
    if not shutil.which("openssl"):
        print(
            "Warning: OpenSSL command line tool not found. Some tests or features might be affected if they rely on it directly."
        )


@pytest.fixture(scope="session")
def certs_base_dir(project_root: Path) -> Path:
    path = project_root / "conformance" / "rpc" / "certs"
    if not path.is_dir():
        pytest.fail(
            f"Certificates directory missing: {path}. "
            "Please ensure certs are generated (e.g., by running gen-certs.sh in conformance/rpc/certs/) and available at this location.",
            pytrace=False,
        )
    return path.resolve()


def _get_cert_paths(certs_dir: Path, prefix: str) -> dict[str, str]:
    """Helper to create a dictionary of paths for a given cert prefix."""
    return {
        "client_cert": str(certs_dir / f"{prefix}-client.crt"),
        "client_key": str(certs_dir / f"{prefix}-client.key"),
        "server_cert": str(certs_dir / f"{prefix}-server.crt"),
        "server_key": str(certs_dir / f"{prefix}-server.key"),
        "server_ca_cert": str(certs_dir / f"{prefix}-server.crt"),
        "client_ca_cert": str(certs_dir / f"{prefix}-client.crt"),
    }


@pytest.fixture(scope="session")
def tls_cert_paths_secp256r1(certs_base_dir: Path) -> dict[str, str]:
    return _get_cert_paths(certs_base_dir, "ec-secp256r1-mtls")


@pytest.fixture(scope="session")
def tls_cert_paths_secp384r1(certs_base_dir: Path) -> dict[str, str]:
    return _get_cert_paths(certs_base_dir, "ec-secp384r1-mtls")


@pytest.fixture(scope="session")
def tls_cert_paths_secp521r1(certs_base_dir: Path) -> dict[str, str]:
    return _get_cert_paths(certs_base_dir, "ec-secp521r1-mtls")


@pytest.fixture(scope="session")
def tls_cert_paths_rsa2048(certs_base_dir: Path) -> dict[str, str]:
    return _get_cert_paths(certs_base_dir, "rsa-2048-mtls")


@pytest.fixture(scope="session")
def tls_cert_paths_rsa4096(certs_base_dir: Path) -> dict[str, str]:
    return _get_cert_paths(certs_base_dir, "rsa-4096-mtls")


# Register Hypothesis profiles for property testing
try:
    from hypothesis import settings

    settings.register_profile("quick", max_examples=10, deadline=10000)
    settings.register_profile("thorough", max_examples=1000, deadline=None)
except ImportError:
    pass  # Hypothesis not installed

# 🥣🔬🔚

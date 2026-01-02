#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Integration between TofuSoup and wrknv.

This module provides functionality to inject TofuSoup's workenv configuration
from soup.toml into wrknv, making wrkenv.toml optional for TofuSoup users.

Note: wrknv is an optional dependency. If not installed, matrix testing features
will be unavailable but other TofuSoup features will work normally."""

from pathlib import Path
import tomllib
from typing import Any

# Optional wrknv import - graceful degradation if not available
try:
    from wrknv import WorkenvConfig  # type: ignore[import-not-found]

    WORKENV_AVAILABLE = True
except ImportError:
    WORKENV_AVAILABLE = False
    WorkenvConfig = None


def load_soup_config(project_root: Path | None = None) -> dict[str, Any]:
    """
    Load the soup.toml configuration file.

    Args:
        project_root: Optional project root directory. If not provided, uses current directory.

    Returns:
        Dictionary containing the soup configuration, or empty dict if not found.
    """
    if project_root is None:
        project_root = Path.cwd()

    soup_toml_path = project_root / "soup.toml"

    if soup_toml_path.exists():
        with soup_toml_path.open("rb") as f:
            return tomllib.load(f)

    return {}


def create_workenv_config_with_soup(project_root: Path | None = None) -> Any:
    """
    Create a WorkenvConfig instance that includes configuration from soup.toml.

    This allows TofuSoup to inject its workenv configuration into wrkenv,
    making wrkenv.toml optional for TofuSoup users.

    Args:
        project_root: Optional project root directory.

    Returns:
        WorkenvConfig instance with soup.toml configuration injected, or None if workenv not available.

    Raises:
        ImportError: If workenv is not installed.
    """
    if not WORKENV_AVAILABLE:
        raise ImportError(
            "wrknv package is not installed. "
            "Matrix testing features require wrknv. "
            "Install with: pip install wrknv (or pip install -e /path/to/wrknv)"
        )

    # Load soup.toml
    soup_config = load_soup_config(project_root)
    workenv_section = soup_config.get("workenv", {})

    if not workenv_section:
        # No workenv config in soup.toml, just return standard WorkenvConfig
        return WorkenvConfig(project_root=project_root)

    # Create a custom ConfigSource for soup.toml
    from wrknv.env.config import FileConfigSource  # type: ignore[import-not-found]

    # Create a soup.toml source
    soup_source = FileConfigSource(
        project_root / "soup.toml" if project_root else Path.cwd() / "soup.toml", "workenv"
    )

    # Create WorkenvConfig and add soup source with highest priority
    config = WorkenvConfig(project_root=project_root)
    config.sources.insert(0, soup_source)  # Insert at beginning for highest priority

    return config


def get_matrix_config_from_soup(project_root: Path | None = None) -> dict[str, Any]:
    """
    Get matrix configuration from soup.toml.

    Args:
        project_root: Optional project root directory.

    Returns:
        Matrix configuration dictionary.
    """
    soup_config = load_soup_config(project_root)
    result: dict[str, Any] = soup_config.get("workenv", {}).get("matrix", {})
    return result


# 🥣🔬🔚

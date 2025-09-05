#
# tofusoup/common/config.py
#
"""
Configuration loading and management for TofuSoup.
"""

import pathlib
import tomllib
from typing import Any

import attrs
from provide.foundation import logger
from provide.foundation.config import BaseConfig, field
from provide.foundation.errors import ConfigurationError
from tofusoup.common.exceptions import TofuSoupConfigError

CONFIG_FILENAME = "soup.toml"
DEFAULT_CONFIG_SUBDIR = "soup"


@attrs.define
class TofuSoupConfig(BaseConfig):
    """Configuration for TofuSoup operations."""
    
    # File paths and directories
    project_root: pathlib.Path | None = field(
        default=None,
        description="Project root directory"
    )
    config_file: str | None = field(
        default=None,
        description="Explicit configuration file path"
    )
    
    # Test configuration
    test_timeout: int = field(
        default=300,
        description="Test timeout in seconds",
        env_var="TOFUSOUP_TEST_TIMEOUT"
    )
    
    # Logging configuration
    log_level: str = field(
        default="INFO",
        description="Logging level",
        env_var="TOFUSOUP_LOG_LEVEL"
    )
    
    @classmethod
    def from_project_root(
        cls, 
        project_root: pathlib.Path, 
        explicit_config_file: str | None = None
    ) -> "TofuSoupConfig":
        """Create config using the traditional TofuSoup loading logic."""
        try:
            config_data = load_tofusoup_config(project_root, explicit_config_file)
            return cls.from_dict(config_data)
        except Exception as e:
            # Fallback to defaults with project info
            return cls(
                project_root=project_root,
                config_file=explicit_config_file
            )


def _load_config_from_file(file_path: pathlib.Path) -> dict[str, Any] | None:
    """
    Attempts to load and parse a TOML configuration file.
    """
    if not file_path.is_file():
        return None

    try:
        logger.info(f"🗣️ Parsing TofuSoup TOML configuration file: {file_path}")
        with open(file_path, "rb") as f:
            config = tomllib.load(f)
        logger.info(
            f"🗣️ Successfully loaded and parsed TOML configuration from {file_path}"
        )
        return config
    except tomllib.TOMLDecodeError as e:
        raise TofuSoupConfigError(
            f"Failed to parse TOML configuration file {file_path}: {e}"
        ) from e
    except Exception as e:
        raise TofuSoupConfigError(
            f"Unexpected error processing configuration file {file_path}: {e}"
        ) from e


def load_tofusoup_config(
    project_root: pathlib.Path, explicit_config_file: str | None = None
) -> dict[str, Any]:
    """
    Loads the TofuSoup configuration according to a specific precedence.
    """
    # 1. Explicit file path from CLI
    if explicit_config_file:
        exp_path = pathlib.Path(explicit_config_file).resolve()
        if exp_path.is_file():
            return _load_config_from_file(exp_path) or {}
        else:
            raise TofuSoupConfigError(
                f"Explicitly specified configuration file not found: {exp_path}"
            )

    # 2. Default path: <project_root>/soup/soup.toml
    default_path = project_root / DEFAULT_CONFIG_SUBDIR / CONFIG_FILENAME
    config = _load_config_from_file(default_path)
    if config is not None:
        return config

    # 3. Fallback path for running from project root: <project_root>/soup.toml
    fallback_path = project_root / CONFIG_FILENAME
    config = _load_config_from_file(fallback_path)
    if config is not None:
        return config

    logger.info(
        "No TofuSoup configuration file found. Using empty default configuration."
    )
    return {}


# 🍲🥄⚙️🪄

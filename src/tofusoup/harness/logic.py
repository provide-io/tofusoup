#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import os
import pathlib
import subprocess
from typing import Any

from provide.foundation import logger
from provide.foundation.process import run as run_command

from tofusoup.common.exceptions import TofuSoupError
from tofusoup.common.utils import get_cache_dir

GO_HARNESS_CONFIG = {
    "soup-go": {
        "source_dir": "src/tofusoup/harness/go/soup-go",
        "main_file": "main.go",
        "output_name": "soup-go",
    },
}


class GoVersionError(TofuSoupError):
    pass


class HarnessBuildError(TofuSoupError):
    pass


class HarnessCleanError(TofuSoupError):
    pass


def _get_effective_go_harness_settings(harness_name: str, loaded_config: dict[str, Any]) -> dict[str, Any]:
    settings: dict[str, Any] = {"build_flags": [], "env_vars": {}}
    component_id = harness_name
    go_defaults = loaded_config.get("harness_defaults", {}).get("go", {})
    settings["build_flags"] = go_defaults.get("build_flags", [])
    settings["env_vars"] = go_defaults.get("common_env_vars", {})

    specific_config = loaded_config.get("harness", {}).get("go", {}).get(component_id, {})
    if "build_flags" in specific_config:
        settings["build_flags"] = specific_config["build_flags"]
    if "env_vars" in specific_config:
        settings["env_vars"].update(specific_config["env_vars"])
    return settings


def ensure_go_harness_build(
    harness_name: str,
    project_root: pathlib.Path,
    loaded_config: dict[str, Any],
    force_rebuild: bool = False,
) -> pathlib.Path:
    config = GO_HARNESS_CONFIG.get(harness_name)
    if not config:
        raise TofuSoupError(f"Configuration for Go harness '{harness_name}' not found.")

    harness_source_path = project_root / config["source_dir"]
    output_bin_dir = get_cache_dir() / "harnesses"
    output_bin_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_bin_dir / config["output_name"]

    if not force_rebuild and output_path.exists():
        logger.info(f"Go harness '{harness_name}' already built at {output_path}. Skipping build.")
        return output_path

    logger.info(f"Building Go harness '{harness_name}' from {harness_source_path}...")

    # Get effective settings for build flags and environment variables
    settings = _get_effective_go_harness_settings(harness_name, loaded_config)
    build_flags = settings["build_flags"]
    env_vars = settings["env_vars"]

    # Construct the build command
    cmd = ["go", "build", "-o", str(output_path)]
    cmd.extend(build_flags)
    cmd.append(str(harness_source_path))

    # Set environment variables for the subprocess
    env = os.environ.copy()
    env.update(env_vars)

    try:
        # Run build command - output not needed, relying on check=True for error handling
        _ = run_command(
            cmd,
            cwd=harness_source_path,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(f"Successfully built Go harness '{harness_name}' to {output_path}")
        return output_path
    except Exception as e:
        # Foundation's run() raises ProcessError, but we want to maintain our custom exceptions
        error_msg = str(e)
        if "not found" in error_msg.lower() or "executable" in error_msg.lower():
            raise GoVersionError(
                "Go executable not found. Please ensure Go is installed and in your PATH."
            ) from e
        logger.error(f"Go build failed for '{harness_name}': {error_msg}")
        raise HarnessBuildError(f"Failed to build Go harness '{harness_name}': {error_msg}") from e


def clean_go_harness_artifacts(harness_name: str, project_root: pathlib.Path) -> None:
    config = GO_HARNESS_CONFIG.get(harness_name)
    if not config:
        raise TofuSoupError(f"Configuration for Go harness '{harness_name}' not found.")

    output_bin_dir = get_cache_dir() / "harnesses"
    output_path = output_bin_dir / config["output_name"]

    if output_path.exists():
        try:
            output_path.unlink()
            logger.info(f"Cleaned Go harness '{harness_name}' at {output_path}")
        except OSError as e:
            logger.error(f"Failed to remove Go harness '{harness_name}': {e}")
            raise HarnessCleanError(f"Failed to clean Go harness '{harness_name}': {e}") from e
    else:
        logger.info(f"Go harness '{harness_name}' not found at {output_path}. Nothing to clean.")


def start_go_plugin_server_process(
    harness_name: str,
    project_root: pathlib.Path,
    loaded_config: dict[str, Any],
    cli_log_level: str | None = None,
    additional_args: list[str] | None = None,
    custom_env: dict[str, str] | None = None,
) -> subprocess.Popen:
    """
    Ensures a Go harness is built and starts it as a server process.
    """
    harness_executable_path = ensure_go_harness_build(harness_name, project_root, loaded_config)

    process_env = os.environ.copy()
    if custom_env:
        process_env.update(custom_env)

    cmd = [str(harness_executable_path)]
    if additional_args:
        cmd.extend(additional_args)

    try:
        return subprocess.Popen(cmd, env=process_env)
    except Exception as e:
        raise TofuSoupError(f"Failed to start Go plugin server '{harness_name}': {e}") from e


# 🥣🔬🔚

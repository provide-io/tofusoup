# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Isolated execution of an OpenTofu experimental lint validation lane."""

import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import tempfile
from typing import Any

from attrs import define

from tofusoup.lint.direct import DiagnosticFinding
from tofusoup.lint.models import LintSuite


class OpenTofuError(RuntimeError):
    """OpenTofu could not prepare or validate an experimental lint fixture."""


@define(frozen=True)
class OpenTofuResult:
    """Parsed output from an isolated ``tofu validate -lint`` invocation."""

    valid: bool
    diagnostics: tuple[DiagnosticFinding, ...]


def _platform_directory() -> str:
    operating_system = {"Darwin": "darwin", "Linux": "linux", "Windows": "windows"}.get(platform.system())
    machine = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64", "AMD64": "amd64"}.get(
        platform.machine()
    )
    if operating_system is None or machine is None:
        raise OpenTofuError(f"unsupported OpenTofu mirror platform: {platform.system()}_{platform.machine()}")
    return f"{operating_system}_{machine}"


def _mirror_destination(root: Path, suite: LintSuite, provider: Path) -> Path:
    source_parts = suite.provider.source.split("/")
    if len(source_parts) != 3 or any(not part for part in source_parts):
        raise OpenTofuError("provider.source must be a registry hostname, namespace, and type")
    destination = root / "mirror" / Path(*source_parts) / suite.provider.version / _platform_directory()
    destination.mkdir(parents=True)
    binary = destination / provider.name
    shutil.copy2(provider, binary)
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    return root / "mirror"


def _write_cli_config(root: Path, mirror: Path, source: str) -> Path:
    config = root / "tofurc"
    config.write_text(
        "provider_installation {\n"
        "  filesystem_mirror {\n"
        f"    path    = {json.dumps(str(mirror))}\n"
        f"    include = [{json.dumps(source)}]\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    return config


def _environment(root: Path, suite: LintSuite, cli_config: Path) -> dict[str, str]:
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("TF_", "TOFU_")) and name not in suite.provider.environment
    }
    environment.update(suite.provider.environment)
    environment.update(
        {
            "TF_CLI_CONFIG_FILE": str(cli_config),
            "TF_DATA_DIR": str(root / "data"),
        }
    )
    Path(environment["TF_DATA_DIR"]).mkdir()
    return environment


def _run(
    command: list[str], cwd: Path, environment: dict[str, str], phase: str
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            command, cwd=cwd, env=environment, capture_output=True, text=True, check=False
        )
    except OSError as error:
        raise OpenTofuError(f"OpenTofu {phase} could not start: {error}") from error
    if completed.returncode != 0:
        output = f"{completed.stdout}{completed.stderr}".strip()
        raise OpenTofuError(f"OpenTofu {phase} failed: {output}")
    return completed


def _resolve_executable(executable: Path) -> Path:
    """Resolve a path or PATH command before entering the temporary fixture."""
    if executable.exists():
        if not executable.is_file():
            raise OpenTofuError(f"OpenTofu executable is not a file: {executable}")
        return executable.resolve()
    resolved = shutil.which(str(executable))
    if resolved is None:
        raise OpenTofuError(f"OpenTofu executable was not found: {executable}")
    return Path(resolved).resolve()


def _diagnostics(raw: Any) -> tuple[DiagnosticFinding, ...]:
    if not isinstance(raw, list):
        raise OpenTofuError("OpenTofu validate JSON did not contain a diagnostics array")
    findings = []
    for diagnostic in raw:
        if not isinstance(diagnostic, dict):
            raise OpenTofuError("OpenTofu validate JSON contained a non-object diagnostic")
        findings.append(
            DiagnosticFinding(
                severity=str(diagnostic.get("severity", "invalid")),
                summary=str(diagnostic.get("summary", "")),
                detail=str(diagnostic.get("detail", "")),
            )
        )
    return tuple(findings)


def run_opentofu(suite: LintSuite, provider: Path, tofu: Path) -> OpenTofuResult:
    """Run the suite's OpenTofu lane without changing its fixture tree."""
    if suite.opentofu is None:
        raise OpenTofuError("the suite does not declare an OpenTofu lint lane")
    tofu = _resolve_executable(tofu)
    with tempfile.TemporaryDirectory(prefix="tofusoup-lint-") as temporary:
        root = Path(temporary)
        mirror = _mirror_destination(root, suite, provider)
        cli_config = _write_cli_config(root, mirror, suite.provider.source)
        fixture = root / "fixture"
        shutil.copytree(suite.opentofu.fixture, fixture)
        environment = _environment(root, suite, cli_config)
        _run([str(tofu), "init", "-backend=false", "-input=false", "-no-color"], fixture, environment, "init")
        completed = _run(
            [str(tofu), "validate", "-json", "-no-color", f"-lint={suite.opentofu.lint}"],
            fixture,
            environment,
            "validate",
        )
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise OpenTofuError(f"OpenTofu validate did not emit JSON: {error}") from error
        if not isinstance(result, dict) or not isinstance(result.get("valid"), bool):
            raise OpenTofuError("OpenTofu validate JSON did not contain a boolean valid field")
        return OpenTofuResult(valid=result["valid"], diagnostics=_diagnostics(result.get("diagnostics", [])))

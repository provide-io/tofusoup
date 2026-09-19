# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Loading and validation for provider lint suite TOML files."""

from collections.abc import Mapping
from pathlib import Path
import tomllib
from typing import Any

from tofusoup.lint.models import (
    ComponentKind,
    DiagnosticExpectation,
    LintSuite,
    OpenTofuSpec,
    ProviderSpec,
    ValidationCase,
)


class SuiteError(ValueError):
    """The lint suite is malformed or violates its semantic contract."""


def _mapping(value: Any, description: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise SuiteError(f"{description} must be a TOML table")
    return value


def _string(value: Any, description: str) -> str:
    if not isinstance(value, str) or not value:
        raise SuiteError(f"{description} must be a non-empty string")
    return value


def _environment(raw: Mapping[str, Any]) -> dict[str, str]:
    environment = raw.get("environment", {})
    if not isinstance(environment, dict):
        raise SuiteError("provider.environment must be a TOML table")
    if any(not isinstance(name, str) or not isinstance(value, str) for name, value in environment.items()):
        raise SuiteError("provider.environment values must be strings")
    return dict(environment)


def _expectations(raw: Any, case_index: int) -> tuple[DiagnosticExpectation, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise SuiteError(f"case {case_index}.expect must be an array")
    expectations = []
    for expectation_index, item in enumerate(raw):
        item_mapping = _mapping(item, f"case {case_index}.expect[{expectation_index}]")
        severity = _string(
            item_mapping.get("severity"), f"case {case_index}.expect[{expectation_index}].severity"
        )
        if severity not in {"warning", "error"}:
            raise SuiteError(
                f"case {case_index}.expect[{expectation_index}].severity must be warning or error"
            )
        expectations.append(
            DiagnosticExpectation(
                severity=severity,
                summary=_string(
                    item_mapping.get("summary"), f"case {case_index}.expect[{expectation_index}].summary"
                ),
            )
        )
    return tuple(expectations)


def _cases(raw: Any) -> tuple[ValidationCase, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise SuiteError("case must be an array of TOML tables")
    cases = []
    for index, item in enumerate(raw):
        mapping = _mapping(item, f"case {index}")
        try:
            kind = ComponentKind(_string(mapping.get("kind"), f"case {index}.kind"))
        except ValueError as error:
            choices = ", ".join(item.value for item in ComponentKind)
            raise SuiteError(f"case {index}.kind must be one of: {choices}") from error
        type_name = mapping.get("type_name")
        if kind.needs_type_name:
            type_name = _string(type_name, f"case {index}.type_name")
        elif type_name is not None:
            raise SuiteError("provider cases must not declare type_name")
        config = mapping.get("config")
        if not isinstance(config, dict):
            raise SuiteError(f"case {index}.config must be a TOML inline table")
        cases.append(
            ValidationCase(
                kind=kind,
                type_name=type_name,
                config=config,
                expect=_expectations(mapping.get("expect"), index),
            )
        )
    return tuple(cases)


def _opentofu(raw: Any, suite_root: Path) -> OpenTofuSpec | None:
    if raw is None:
        return None
    mapping = _mapping(raw, "opentofu")
    fixture = (suite_root / _string(mapping.get("fixture"), "opentofu.fixture")).resolve()
    if not fixture.is_relative_to(suite_root.resolve()):
        raise SuiteError("opentofu.fixture must be inside the suite directory")
    if not fixture.is_dir():
        raise SuiteError(f"opentofu.fixture does not exist: {fixture}")
    return OpenTofuSpec(fixture=fixture, lint=_string(mapping.get("lint"), "opentofu.lint"))


def load_suite(path: Path) -> LintSuite:
    """Load a version-one lint suite from ``path``."""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise SuiteError(f"could not read lint suite {path}: {error}") from error
    if raw.get("version") != 1:
        raise SuiteError("only lint suite version 1 is supported")
    provider = _mapping(raw.get("provider"), "provider")
    return LintSuite(
        version=1,
        provider=ProviderSpec(
            source=_string(provider.get("source"), "provider.source"),
            environment=_environment(provider),
        ),
        cases=_cases(raw.get("case")),
        opentofu=_opentofu(raw.get("opentofu"), path.parent),
    )

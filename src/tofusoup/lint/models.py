# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Immutable data model for provider lint suites."""

from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any

from attrs import define, field


class ComponentKind(StrEnum):
    """Provider configuration-validation RPC kinds supported by tfprotov6."""

    PROVIDER = "provider"
    RESOURCE = "resource"
    DATA_SOURCE = "data-source"
    EPHEMERAL = "ephemeral"
    LIST = "list"
    ACTION = "action"
    STATE_STORE = "state-store"

    @property
    def needs_type_name(self) -> bool:
        """Whether this RPC kind requires a schema type name."""
        return self is not ComponentKind.PROVIDER


@define(frozen=True)
class DiagnosticExpectation:
    """A finding a declared validation case must return."""

    severity: str
    summary: str


@define(frozen=True)
class ProviderSpec:
    """Provider identity and explicitly declared child environment."""

    source: str
    environment: Mapping[str, str] = field(factory=dict)


@define(frozen=True)
class ValidationCase:
    """One direct provider configuration-validation request."""

    kind: ComponentKind
    config: Mapping[str, Any]
    type_name: str | None = None
    expect: Sequence[DiagnosticExpectation] = field(factory=tuple)


@define(frozen=True)
class OpenTofuSpec:
    """Native OpenTofu lint fixture and requested lint selector."""

    fixture: Path
    lint: str


@define(frozen=True)
class LintSuite:
    """Parsed version-one provider lint suite."""

    version: int
    provider: ProviderSpec
    cases: Sequence[ValidationCase]
    opentofu: OpenTofuSpec | None = None

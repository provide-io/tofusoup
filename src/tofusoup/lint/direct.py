# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Direct tfprotov6 provider validation dispatch."""

from collections.abc import Mapping
from typing import Any

from attrs import define

from pyvider.protocols.tfprotov6.protobuf import tfplugin6_pb2 as pb
from tofusoup.lint.models import ComponentKind, ValidationCase
from tofusoup.tfplugin.driver import pack


@define(frozen=True)
class DiagnosticFinding:
    """A provider diagnostic rendered without a protobuf dependency."""

    severity: str
    summary: str
    detail: str


@define(frozen=True)
class DirectCaseResult:
    """Diagnostics returned for one declared validation case."""

    kind: ComponentKind
    type_name: str | None
    diagnostics: tuple[DiagnosticFinding, ...]


DIRECT_METHODS: Mapping[ComponentKind, tuple[str, type[Any]]] = {
    ComponentKind.PROVIDER: ("ValidateProviderConfig", pb.ValidateProviderConfig.Request),
    ComponentKind.RESOURCE: ("ValidateResourceConfig", pb.ValidateResourceConfig.Request),
    ComponentKind.DATA_SOURCE: ("ValidateDataResourceConfig", pb.ValidateDataResourceConfig.Request),
    ComponentKind.EPHEMERAL: ("ValidateEphemeralResourceConfig", pb.ValidateEphemeralResourceConfig.Request),
    ComponentKind.LIST: ("ValidateListResourceConfig", pb.ValidateListResourceConfig.Request),
    ComponentKind.ACTION: ("ValidateActionConfig", pb.ValidateActionConfig.Request),
    ComponentKind.STATE_STORE: ("ValidateStateStoreConfig", pb.ValidateStateStore.Request),
}


def _severity(diagnostic: pb.Diagnostic) -> str:
    if diagnostic.severity == pb.Diagnostic.ERROR:
        return "error"
    if diagnostic.severity == pb.Diagnostic.WARNING:
        return "warning"
    return "invalid"


def _request(case: ValidationCase) -> tuple[str, Any]:
    method_name, request_type = DIRECT_METHODS[case.kind]
    fields: dict[str, Any] = {"config": pack(dict(case.config))}
    if case.type_name is not None:
        fields["type_name"] = case.type_name
    return method_name, request_type(**fields)


async def run_direct_case(provider: Any, case: ValidationCase) -> DirectCaseResult:
    """Invoke exactly one validation RPC declared by ``case``."""
    method_name, request = _request(case)
    response = await getattr(provider.stub, method_name)(request)
    diagnostics = tuple(
        DiagnosticFinding(
            severity=_severity(diagnostic),
            summary=diagnostic.summary,
            detail=diagnostic.detail,
        )
        for diagnostic in response.diagnostics
    )
    return DirectCaseResult(kind=case.kind, type_name=case.type_name, diagnostics=diagnostics)

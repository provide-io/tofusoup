# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Direct tfprotov6 provider validation dispatch."""

from collections.abc import Mapping
from typing import Any

from attrs import define

from pyvider.protocols.tfprotov6.protobuf import tfplugin6_pb2 as pb
from tofusoup.lint.models import ComponentKind, ValidationCase
from tofusoup.tfplugin.driver import base_env, pack, start_provider


class DirectLintError(RuntimeError):
    """The provider could not prepare or complete a direct lint suite lane."""


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


@define(frozen=True)
class DirectSuiteResult:
    """All direct validation cases from one suite run."""

    cases: tuple[DirectCaseResult, ...]
    failures: tuple[str, ...]


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


def _label(case: ValidationCase) -> str:
    return case.kind.value if case.type_name is None else f"{case.kind.value} {case.type_name}"


def case_failures(case: ValidationCase, result: DirectCaseResult) -> tuple[str, ...]:
    """Return the failed lint contract assertions for one direct case."""
    label = _label(case)
    failures = [
        f"{label} returned an error diagnostic: {diagnostic.summary}"
        for diagnostic in result.diagnostics
        if diagnostic.severity == "error"
    ]
    for expectation in case.expect:
        if not any(
            diagnostic.severity == expectation.severity and diagnostic.summary == expectation.summary
            for diagnostic in result.diagnostics
        ):
            failures.append(f"{label} did not return expected {expectation.severity}: {expectation.summary}")
    return tuple(failures)


def _raise_for_errors(phase: str, diagnostics: Any) -> None:
    messages = [diagnostic.summary for diagnostic in diagnostics if diagnostic.severity == pb.Diagnostic.ERROR]
    if messages:
        raise DirectLintError(f"provider {phase} failed: {'; '.join(messages)}")


async def run_direct_suite(suite: Any, binary: Any) -> DirectSuiteResult:
    """Launch one provider and execute every validation case in ``suite``."""
    provider = await start_provider(binary, env=base_env(dict(suite.provider.environment)))
    try:
        schema = await provider.stub.GetProviderSchema(pb.GetProviderSchema.Request())
        _raise_for_errors("schema lookup", schema.diagnostics)
        provider.schema = schema
        provider_case = next((case for case in suite.cases if case.kind is ComponentKind.PROVIDER), None)
        configuration = {} if provider_case is None else dict(provider_case.config)
        configured = await provider.stub.ConfigureProvider(
            pb.ConfigureProvider.Request(terraform_version="tofusoup", config=pack(configuration))
        )
        _raise_for_errors("configuration", configured.diagnostics)
        cases = tuple([await run_direct_case(provider, case) for case in suite.cases])
        failures = tuple(
            failure
            for case, result in zip(suite.cases, cases, strict=True)
            for failure in case_failures(case, result)
        )
        return DirectSuiteResult(cases=cases, failures=failures)
    finally:
        await provider.stop()

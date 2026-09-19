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

SCHEMA_COLLECTIONS: Mapping[ComponentKind, tuple[str, str | None]] = {
    ComponentKind.RESOURCE: ("resource_schemas", None),
    ComponentKind.DATA_SOURCE: ("data_source_schemas", None),
    ComponentKind.EPHEMERAL: ("ephemeral_resource_schemas", None),
    ComponentKind.LIST: ("list_resource_schemas", None),
    ComponentKind.ACTION: ("action_schemas", "schema"),
    ComponentKind.STATE_STORE: ("state_store_schemas", None),
}


def _severity(diagnostic: pb.Diagnostic) -> str:
    if diagnostic.severity == pb.Diagnostic.ERROR:
        return "error"
    if diagnostic.severity == pb.Diagnostic.WARNING:
        return "warning"
    return "invalid"


def _case_schema(provider: Any, case: ValidationCase) -> Any | None:
    schema = getattr(provider, "schema", None)
    if schema is None:
        return None
    if case.kind is ComponentKind.PROVIDER:
        return schema.provider
    if case.type_name is None:
        raise DirectLintError(f"{case.kind.value} requires a type name")
    try:
        collection_name, nested_schema_name = SCHEMA_COLLECTIONS[case.kind]
        component_schema = getattr(schema, collection_name)[case.type_name]
        return (
            component_schema if nested_schema_name is None else getattr(component_schema, nested_schema_name)
        )
    except KeyError as error:
        raise DirectLintError(f"provider schema has no {case.kind.value} named {case.type_name}") from error
    raise DirectLintError(f"unsupported validation kind: {case.kind.value}")


def _config(provider: Any, case: ValidationCase) -> dict[str, Any]:
    schema = _case_schema(provider, case)
    values = {} if schema is None else {attribute.name: None for attribute in schema.block.attributes}
    values.update(case.config)
    return values


def _request(provider: Any, case: ValidationCase) -> tuple[str, Any]:
    method_name, request_type = DIRECT_METHODS[case.kind]
    fields: dict[str, Any] = {"config": pack(_config(provider, case))}
    if case.type_name is not None:
        fields["type_name"] = case.type_name
    return method_name, request_type(**fields)


async def run_direct_case(provider: Any, case: ValidationCase) -> DirectCaseResult:
    """Invoke exactly one validation RPC declared by ``case``."""
    method_name, request = _request(provider, case)
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
        configuration = _config(
            provider,
            provider_case if provider_case is not None else ValidationCase(kind=ComponentKind.PROVIDER),
        )
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

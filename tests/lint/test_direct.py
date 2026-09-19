# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib
from types import SimpleNamespace

import pytest

from pyvider.protocols.tfprotov6.protobuf import tfplugin6_pb2 as pb
from tofusoup.lint.models import (
    ComponentKind,
    DiagnosticExpectation,
    LintSuite,
    ProviderSpec,
    ValidationCase,
)


class RecordingStub:
    """Records generic validation calls and returns one warning finding."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def __getattr__(self, name: str):
        async def call(request: object):
            self.calls.append((name, request))
            response_type = {
                "ValidateProviderConfig": pb.ValidateProviderConfig.Response,
                "ValidateResourceConfig": pb.ValidateResourceConfig.Response,
                "ValidateDataResourceConfig": pb.ValidateDataResourceConfig.Response,
                "ValidateEphemeralResourceConfig": pb.ValidateEphemeralResourceConfig.Response,
                "ValidateListResourceConfig": pb.ValidateListResourceConfig.Response,
                "ValidateActionConfig": pb.ValidateActionConfig.Response,
                "ValidateStateStoreConfig": pb.ValidateStateStore.Response,
            }[name]
            return response_type(
                diagnostics=[
                    pb.Diagnostic(
                        severity=pb.Diagnostic.WARNING,
                        summary="Example lint finding",
                    )
                ]
            )

        return call


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "method", "request_type"),
    [
        (ComponentKind.PROVIDER, "ValidateProviderConfig", pb.ValidateProviderConfig.Request),
        (ComponentKind.RESOURCE, "ValidateResourceConfig", pb.ValidateResourceConfig.Request),
        (ComponentKind.DATA_SOURCE, "ValidateDataResourceConfig", pb.ValidateDataResourceConfig.Request),
        (
            ComponentKind.EPHEMERAL,
            "ValidateEphemeralResourceConfig",
            pb.ValidateEphemeralResourceConfig.Request,
        ),
        (ComponentKind.LIST, "ValidateListResourceConfig", pb.ValidateListResourceConfig.Request),
        (ComponentKind.ACTION, "ValidateActionConfig", pb.ValidateActionConfig.Request),
        (ComponentKind.STATE_STORE, "ValidateStateStoreConfig", pb.ValidateStateStore.Request),
    ],
)
async def test_direct_runner_dispatches_declared_validation_rpc(kind, method, request_type) -> None:
    try:
        direct = importlib.import_module("tofusoup.lint.direct")
    except ModuleNotFoundError:
        pytest.fail("direct provider lint runner has not been implemented")
    stub = RecordingStub()
    case = ValidationCase(
        kind=kind,
        type_name=None if kind is ComponentKind.PROVIDER else "example_type",
        config={"enabled": True},
    )

    result = await direct.run_direct_case(SimpleNamespace(stub=stub), case)

    assert stub.calls[0][0] == method
    assert isinstance(stub.calls[0][1], request_type)
    assert result.kind is kind
    assert result.diagnostics[0].summary == "Example lint finding"


@pytest.mark.asyncio
async def test_direct_suite_configures_provider_and_stops_it(monkeypatch, tmp_path) -> None:
    direct = importlib.import_module("tofusoup.lint.direct")
    stub = RecordingStub()
    calls: list[str] = []

    async def get_schema(request):
        calls.append("GetProviderSchema")
        return pb.GetProviderSchema.Response()

    async def configure_provider(request):
        calls.append("ConfigureProvider")
        return pb.ConfigureProvider.Response()

    stub.GetProviderSchema = get_schema
    stub.ConfigureProvider = configure_provider

    class Provider:
        schema = None

        def __init__(self):
            self.stub = stub
            self.stopped = False

        async def stop(self) -> None:
            self.stopped = True

    provider = Provider()

    async def start_provider(binary, env):
        assert binary == tmp_path / "provider"
        assert env["EXAMPLE_LINT"] == "example:all"
        return provider

    suite = LintSuite(
        version=1,
        provider=ProviderSpec(
            source="registry.opentofu.org/example/demo",
            version="1.2.3",
            environment={"EXAMPLE_LINT": "example:all"},
        ),
        cases=(ValidationCase(kind=ComponentKind.PROVIDER, config={}),),
    )

    assert getattr(direct, "run_direct_suite", None) is not None
    monkeypatch.setattr(direct, "start_provider", start_provider)
    result = await direct.run_direct_suite(suite, tmp_path / "provider")

    assert calls == ["GetProviderSchema", "ConfigureProvider"]
    assert stub.calls[0][0] == "ValidateProviderConfig"
    assert len(result.cases) == 1
    assert provider.stopped is True


def test_direct_case_evaluation_rejects_error_and_missing_expected_finding() -> None:
    direct = importlib.import_module("tofusoup.lint.direct")
    case = ValidationCase(
        kind=ComponentKind.RESOURCE,
        type_name="example_thing",
        config={},
        expect=(DiagnosticExpectation(severity="warning", summary="Required warning"),),
    )
    result = SimpleNamespace(
        diagnostics=(SimpleNamespace(severity="error", summary="Provider error", detail="detail"),)
    )

    failures = direct.case_failures(case, result)

    assert failures == (
        "resource example_thing returned an error diagnostic: Provider error",
        "resource example_thing did not return expected warning: Required warning",
    )

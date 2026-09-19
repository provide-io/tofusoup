# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib
from types import SimpleNamespace

import pytest

from pyvider.protocols.tfprotov6.protobuf import tfplugin6_pb2 as pb
from tofusoup.lint.models import ComponentKind, ValidationCase


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

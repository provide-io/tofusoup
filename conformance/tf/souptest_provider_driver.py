#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Conformance checks any tfplugin6 provider binary must pass.

Deliberately provider-agnostic: it asserts only what the protocol itself
guarantees, so it can be pointed at any provider. Point it at one with:

    TOFUSOUP_TFPLUGIN_BINARY=/path/to/terraform-provider-foo \
        pytest conformance/tf/souptest_provider_driver.py

Provider-specific behaviour belongs with that provider -- see
terraform-provider-pyvider's own conformance suite, which builds on this driver.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
import os
from pathlib import Path

import pytest
import pytest_asyncio

from pyvider.protocols.tfprotov6.protobuf import tfplugin6_pb2 as pb
from tofusoup.tfplugin import TfPluginProvider, base_env, errors, start_provider

BINARY_ENV = "TOFUSOUP_TFPLUGIN_BINARY"
EXTRA_ENV_PREFIX = "TOFUSOUP_TFPLUGIN_ENV_"

pytestmark = pytest.mark.asyncio(loop_scope="module")


def _extra_env() -> dict[str, str]:
    """Pass provider-specific variables through without knowing what they are.

    A provider may need its own environment (a test-mode flag, a credential) to
    serve a useful schema. Naming them here would make this suite specific to
    one provider, so they arrive prefixed instead.
    """
    return {
        name[len(EXTRA_ENV_PREFIX) :]: value
        for name, value in os.environ.items()
        if name.startswith(EXTRA_ENV_PREFIX)
    }


@pytest.fixture(scope="module")
def provider_binary() -> Path:
    configured = os.environ.get(BINARY_ENV)
    if not configured:
        pytest.skip(f"set {BINARY_ENV} to a tfplugin6 provider binary to run these")
    path = Path(configured)
    if not path.exists():
        pytest.skip(f"{BINARY_ENV} points at {path}, which does not exist")
    return path


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def provider(provider_binary: Path) -> AsyncIterator[TfPluginProvider]:
    session = await start_provider(provider_binary, env=base_env(_extra_env()))
    try:
        yield session
    finally:
        await session.stop()


async def test_negotiates_protocol_six(provider: TfPluginProvider) -> None:
    """A tfplugin6 provider must land on 6, not fall back to the default of 1."""
    assert provider.protocol_version == 6


async def test_serves_over_an_advertised_transport(provider: TfPluginProvider) -> None:
    assert provider.transport in {"unix", "tcp"}


async def test_returns_a_provider_schema(provider: TfPluginProvider) -> None:
    """Every provider has a schema, and it must arrive without error diagnostics."""
    response = await provider.stub.GetProviderSchema(pb.GetProviderSchema.Request())

    assert not errors(response.diagnostics)
    assert response.HasField("provider")


async def test_metadata_agrees_with_the_schema(provider: TfPluginProvider) -> None:
    """A type advertised by one discovery RPC but not the other is unusable.

    The two are built from separate code paths in most providers, so they drift.
    """
    schema = await provider.stub.GetProviderSchema(pb.GetProviderSchema.Request())
    metadata = await provider.stub.GetMetadata(pb.GetMetadata.Request())

    assert {r.type_name for r in metadata.resources} == set(schema.resource_schemas)
    assert {d.type_name for d in metadata.data_sources} == set(schema.data_source_schemas)


async def test_unknown_resource_type_is_reported_not_ignored(provider: TfPluginProvider) -> None:
    """An unregistered type must produce a diagnostic rather than a silent pass."""
    response = await provider.stub.ValidateResourceConfig(
        pb.ValidateResourceConfig.Request(type_name="tofusoup_definitely_not_a_real_type")
    )

    assert errors(response.diagnostics)


# 🥣🔬🔚

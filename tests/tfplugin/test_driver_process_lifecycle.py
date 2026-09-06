#
# SPDX-FileCopyrightText: Copyright (c) 2025-2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""A launch that fails must not leave the plugin process behind.

start_provider spawns a child before the handshake completes. If the handshake
raises, the caller never receives the client and so has no way to stop what was
spawned: the process outlives the test session, and the threads reading its
stderr are non-daemon, so the interpreter cannot finish shutting down while one
of them is blocked reading a pipe the orphan still holds open.
"""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from tofusoup.tfplugin.driver import start_provider


class _ClientThatFailsToStart:
    """Stands in for RPCPluginClient: spawns on construction, fails to hand over."""

    instances: ClassVar[list[_ClientThatFailsToStart]] = []

    def __init__(self, **_kwargs: Any) -> None:
        self.closed = False
        self.grpc_channel = object()
        type(self).instances.append(self)

    async def start(self) -> None:
        raise RuntimeError("handshake never completed")

    async def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def _no_leaked_instances() -> Any:
    _ClientThatFailsToStart.instances.clear()
    yield
    _ClientThatFailsToStart.instances.clear()


async def test_a_failed_start_closes_the_client_it_created(monkeypatch: pytest.MonkeyPatch) -> None:
    """The spawned process is the caller's only handle on the child."""
    monkeypatch.setattr("pyvider.rpcplugin.RPCPluginClient", _ClientThatFailsToStart)

    with pytest.raises(RuntimeError, match="handshake never completed"):
        await start_provider("/nonexistent/provider")

    assert _ClientThatFailsToStart.instances, "the driver never constructed a client"
    client = _ClientThatFailsToStart.instances[0]
    assert client.closed, "start_provider left the plugin process with nobody able to stop it"


# 🥣🔬🔚

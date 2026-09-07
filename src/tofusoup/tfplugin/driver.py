#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""A tfplugin6 client for a packaged provider binary.

Handshake, transport selection, and mTLS are delegated to `pyvider-rpcplugin`'s
client, which is the same code path a Go client exercises; reimplementing them
here would test the reimplementation rather than the provider.

Nothing in this module knows about any particular provider. Callers supply the
binary and whatever environment it needs, and assert against the responses.
"""

from __future__ import annotations

from contextlib import suppress
import json
import ntpath
import os
from pathlib import Path
import tempfile
from typing import Any

from attrs import define, field
import msgpack

from pyvider.protocols.tfprotov6.protobuf import tfplugin6_pb2 as pb, tfplugin6_pb2_grpc as pb_grpc

#: Terraform's own magic cookie. A provider refuses to serve without it, which
#: is the point: it stops a plugin binary being run as an ordinary command.
MAGIC_COOKIE_KEY = "TF_PLUGIN_MAGIC_COOKIE"
MAGIC_COOKIE_VALUE = "d602bf8f470bc67ca7faa0386276bbdd4330efaf76d1a219cb4d6991ca9872b2"

#: Protocol versions to offer, mirroring what Terraform 1.14+ sends. The server
#: picks the highest it shares; offering nothing lands on version 1.
DEFAULT_PROTOCOL_VERSIONS = "6"


#: PATH for the child. Deliberately *not* inherited: a packaged provider may
#: resolve its own entry point through PATH, so an active virtualenv on the
#: caller's PATH can shadow the bundled runtime. The provider then serves from
#: whatever is installed in that environment rather than from the artifact under
#: test, which silently turns a conformance run into a test of the developer's
#: working tree. Pass "PATH" in `extra` to opt back in.
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"

#: Variables a Windows process needs from its parent. A leave-one-out bisect on
#: the runner proved two of these are required, each with its own failure:
#:
#:   SYSTEMROOT   OSError: [WinError 10106] The requested service provider could
#:                not be loaded or initialized -- Winsock, so a gRPC server
#:                exits before writing its handshake line.
#:   USERPROFILE  RuntimeError: Could not determine home directory, out of
#:                pathlib. `ntpath.expanduser` reads USERPROFILE and ignores
#:                HOME, so passing HOME alone does not answer this on Windows.
#:
#: The rest are carried rather than proven necessary: they cost nothing, and
#: TEMP in particular is the name Windows reads for a scratch directory where
#: the TMPDIR set below is the POSIX one. Scrubbing PATH is this function's
#: purpose; scrubbing these is not.
WINDOWS_ESSENTIAL_VARS = (
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "LOCALAPPDATA",
    "APPDATA",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
)


def _system_path() -> str:
    """The scrubbed PATH for the running platform.

    A POSIX PATH resolves nothing on Windows, which leaves the launcher to find
    its interpreter by absolute path and every other lookup to fail. Build the
    Windows equivalent from `SystemRoot` rather than writing a drive letter down.
    """
    if os.name != "nt":
        return SYSTEM_PATH
    # Windows resolves environment names case-insensitively, so the canonical
    # mixed-case spelling and this one name the same variable.
    root = os.environ.get("SYSTEMROOT", "")
    if not root:
        # Not the caller's PATH. Handing that back is exactly what this function
        # exists to withhold -- an active virtualenv on it can shadow the bundled
        # runtime -- and a lookup failing is no reason to abandon the scrub. An
        # empty PATH is the honest scrubbed answer, and it is what Windows has
        # been given all along, since a POSIX PATH resolves nothing there; the
        # launcher finds its interpreter by absolute path regardless.
        return ""
    # ntpath rather than pathlib: this branch is exercised from every platform,
    # and pathlib would build the host's flavour of path instead of Windows'.
    system32 = ntpath.join(root, "System32")
    return ntpath.pathsep.join([system32, root, ntpath.join(system32, "Wbem")])


def _home() -> str:
    """HOME for the child, falling back to the Windows profile when unset.

    An empty HOME is worse than a missing one: flavor's launcher reads it before
    it reaches its own Windows branch, and joins the empty value into a relative
    cache directory that lands wherever the child happens to be running.
    """
    home = os.environ.get("HOME", "")
    if home or os.name != "nt":
        return home
    return os.environ.get("USERPROFILE", "")


def base_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build the environment a provider process is launched with.

    Deliberately minimal rather than a copy of `os.environ`: it makes the
    variables a provider actually depends on explicit, so a packaging step that
    drops one shows up as a failure here rather than as a mystery later.
    """
    env = {
        "PATH": _system_path(),
        "HOME": _home(),
        # `gettempdir` rather than a literal: it already consults TMPDIR, and
        # falls back to the platform's own answer instead of assuming a POSIX
        # layout -- which is also what stops bandit reading this as a hardcoded
        # temp path (B108).
        "TMPDIR": tempfile.gettempdir(),
        "PLUGIN_PROTOCOL_VERSIONS": DEFAULT_PROTOCOL_VERSIONS,
    }
    if os.name == "nt":
        env.update({name: os.environ[name] for name in WINDOWS_ESSENTIAL_VARS if name in os.environ})
    if extra:
        env.update(extra)
    return env


def pack(values: Any) -> pb.DynamicValue:
    """Encode a value the way Terraform encodes config and state."""
    return pb.DynamicValue(msgpack=msgpack.packb(values, use_bin_type=True))


def unpack(value: pb.DynamicValue) -> Any:
    """Decode a DynamicValue in whichever encoding it arrived in.

    DynamicValue carries msgpack *or* json, and providers legitimately use both:
    state upgrades and moves pass raw JSON straight through, while everything
    planned or applied is msgpack. A decoder that understood only one would read
    the other as an empty value.
    """
    if value.msgpack:
        return msgpack.unpackb(value.msgpack, raw=False, strict_map_key=False)
    if value.json:
        return json.loads(value.json)
    return None


def diagnostic_text(diagnostics: Any) -> str:
    """Render diagnostics into one string, for assertion messages."""
    return " | ".join(f"{d.severity}:{d.summary}:{d.detail}" for d in diagnostics)


def errors(diagnostics: Any) -> list[Any]:
    """Only the ERROR-severity diagnostics."""
    return [d for d in diagnostics if d.severity == pb.Diagnostic.ERROR]


@define
class TfPluginProvider:
    """A running provider process plus a stub bound to its gRPC channel."""

    client: Any = field()
    stub: pb_grpc.ProviderStub = field()
    schema: pb.GetProviderSchema.Response | None = field(default=None)

    @property
    def protocol_version(self) -> int | None:
        version: int | None = self.client._protocol_version
        return version

    @property
    def transport(self) -> str | None:
        name: str | None = self.client._transport_name
        return name

    def provider_config(self, **overrides: Any) -> pb.DynamicValue:
        """Build a provider config with every declared attribute present.

        Terraform sends the whole block with nulls for anything unset; a partial
        map is not a smaller version of that, it is a different value, and a
        provider is entitled to reject it.
        """
        if self.schema is None:
            raise RuntimeError("fetch the provider schema before building a config")
        values: dict[str, Any] = {a.name: None for a in self.schema.provider.block.attributes}
        values.update(overrides)
        return pack(values)

    async def stop(self) -> None:
        await self.client.shutdown_plugin()
        await self.client.close()


async def start_provider(
    binary: str | Path,
    env: dict[str, str] | None = None,
    magic_cookie_key: str = MAGIC_COOKIE_KEY,
    magic_cookie_value: str = MAGIC_COOKIE_VALUE,
) -> TfPluginProvider:
    """Launch a provider binary and complete the go-plugin handshake.

    Args:
        binary: The provider executable, e.g. a packaged `.psp`.
        env: Environment for the child. Defaults to `base_env()`.
        magic_cookie_key / magic_cookie_value: Override only when driving a
            plugin that uses a different handshake cookie from Terraform's.
    """
    from pyvider.rpcplugin import RPCPluginClient
    from pyvider.rpcplugin.config import rpcplugin_config

    rpcplugin_config.plugin_magic_cookie_key = magic_cookie_key
    rpcplugin_config.plugin_magic_cookie_value = magic_cookie_value

    client = RPCPluginClient(command=[str(binary)], config={"env": env or base_env()})
    try:
        await client.start()
    except BaseException:
        # The client is the only handle on a process that may already be
        # running: a caller that never receives it cannot stop it. An orphan
        # keeps its stderr pipe open, and the threads reading that pipe are
        # not daemons, so the interpreter cannot finish shutting down while
        # one of them is blocked on a read that will never return.
        with suppress(Exception):
            await client.close()
        raise
    return TfPluginProvider(client=client, stub=pb_grpc.ProviderStub(client.grpc_channel))


# 🥣🔬🔚

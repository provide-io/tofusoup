"""A child built from `base_env()` alone has to be one the OS can start.

The unit tests beside this one assert the contents of a dictionary. That is not
the guarantee the comment above `WINDOWS_ESSENTIAL_VARS` makes, and the two can
disagree without anything failing: every caller in this repository hands the
dict to `RPCPluginClient`, whose `ManagedProcess` independently starts from
`os.environ.copy()`, so a variable could be dropped or misspelled and the real
path would still work because the parent supplied it.

These launch a real process with exactly `env=base_env()` and nothing else. On
Windows CI that is the guarantee itself: a process without `SystemRoot` cannot
initialise Winsock, so it dies before a gRPC server prints its handshake line.

SPDX-FileCopyrightText: Copyright (c) 2025-2026 provide.io llc. All rights reserved.
SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import os
import subprocess
import sys

from tofusoup.tfplugin.driver import base_env

#: Bind a socket and report the port. Binding is the point: it forces the
#: networking stack to initialise, which is the step a scrubbed Windows
#: environment breaks and the step a provider reaches before it says anything.
PROBE = (
    "import socket, sys\n"
    "s = socket.socket()\n"
    "s.bind(('127.0.0.1', 0))\n"
    "sys.stdout.write(str(s.getsockname()[1]))\n"
)


def _run(code: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_a_child_starts_from_base_env_alone() -> None:
    """The standalone-caller guarantee, exercised rather than asserted."""
    result = _run(PROBE, base_env())

    assert result.returncode == 0, f"child failed to start: {result.stderr}"
    assert int(result.stdout.strip()) > 0


def test_that_child_can_open_a_socket() -> None:
    """Winsock initialises, which is what `SystemRoot` is forwarded for."""
    result = _run(PROBE, base_env())

    assert result.returncode == 0, result.stderr
    port = int(result.stdout.strip())
    assert 1 <= port <= 65535


def test_extra_reaches_the_child() -> None:
    """`extra` is how a caller adds what the scrub does not carry."""
    code = "import os, sys; sys.stdout.write(os.environ.get('TOFUSOUP_MARKER', ''))"

    result = _run(code, base_env({"TOFUSOUP_MARKER": "carried"}))

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "carried"


def test_the_scrub_is_real(monkeypatch) -> None:
    """A variable the parent carries does not reach a child of this dict.

    Without this the launch test above would pass on an environment that was
    never scrubbed at all.
    """
    monkeypatch.setenv("TOFUSOUP_SHOULD_NOT_TRAVEL", "leaked")
    code = "import os, sys; sys.stdout.write(os.environ.get('TOFUSOUP_SHOULD_NOT_TRAVEL', 'absent'))"

    result = _run(code, base_env())

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "absent"


def test_the_launch_path_does_not_share_this_contract() -> None:
    """`ManagedProcess` inherits the parent environment; `base_env` replaces it.

    Pinned because the difference is what lets the dictionary tests pass while
    a standalone caller fails. If the launch path ever stops inheriting, the
    forwarding in `base_env` becomes load-bearing rather than belt-and-braces,
    and this failing is the signal to re-read both.
    """
    import inspect

    from provide.foundation.process import ManagedProcess

    source = inspect.getsource(ManagedProcess)

    assert "os.environ.copy()" in source


def test_every_forwarded_windows_variable_is_one_the_parent_has() -> None:
    """The forwarding list only ever copies, so it cannot invent a value."""
    from tofusoup.tfplugin.driver import WINDOWS_ESSENTIAL_VARS

    env = base_env()

    for name in WINDOWS_ESSENTIAL_VARS:
        if name in env and name in os.environ:
            assert env[name] == os.environ[name]

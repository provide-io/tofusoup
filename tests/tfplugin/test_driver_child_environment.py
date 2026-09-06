"""The environment a provider is launched with has to be one the OS can start.

`base_env` deliberately scrubs the caller's environment. On Windows that scrub
removed variables the platform itself requires: a process without `SystemRoot`
cannot initialise Winsock, so a gRPC server exits before printing its handshake
line. The conformance suite saw this as every test failing on one handshake
timeout, while a launch that inherited the environment served in about a second.

These drive the Windows branch through a patched `os.name` so they fail on any
platform rather than only on the one that was broken.

SPDX-FileCopyrightText: Copyright (c) 2025-2026 provide.io llc. All rights reserved.
SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import pytest

from tofusoup.tfplugin.driver import base_env

WINDOWS_ROOT = r"C:\Windows"


@pytest.fixture
def windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Present a Windows platform carrying the variables a real runner has."""
    monkeypatch.setattr("tofusoup.tfplugin.driver.os.name", "nt")
    monkeypatch.setenv("SYSTEMROOT", WINDOWS_ROOT)
    monkeypatch.setenv("PATHEXT", ".COM;.EXE;.BAT")
    monkeypatch.setenv("TEMP", r"C:\Users\runner\AppData\Local\Temp")
    monkeypatch.setenv("USERPROFILE", r"C:\Users\runner")
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\runner\AppData\Local")
    monkeypatch.delenv("HOME", raising=False)


def test_windows_child_can_reach_winsock(windows: None) -> None:
    """Without SystemRoot the child cannot open a socket, so it must be passed."""
    assert base_env()["SYSTEMROOT"] == WINDOWS_ROOT


def test_windows_child_gets_an_executable_suffix_list(windows: None) -> None:
    assert base_env()["PATHEXT"] == ".COM;.EXE;.BAT"


def test_windows_path_names_the_platform_system_directory(windows: None) -> None:
    """A POSIX PATH resolves nothing on Windows; the system directory must."""
    path = base_env()["PATH"]
    assert "system32" in path.lower()
    assert "/usr/bin" not in path


def test_windows_home_falls_back_to_the_user_profile(windows: None) -> None:
    """An empty HOME makes flavor's launcher resolve a relative cache directory."""
    assert base_env()["HOME"] == r"C:\Users\runner"


def test_windows_child_gets_a_temp_directory_windows_reads(windows: None) -> None:
    """Windows reads TEMP/TMP; TMPDIR alone leaves it with no writable scratch."""
    assert base_env()["TEMP"]


def test_posix_environment_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """The scrub is the point of this function everywhere it already worked."""
    monkeypatch.setattr("tofusoup.tfplugin.driver.os.name", "posix")
    monkeypatch.setenv("HOME", "/home/runner")
    env = base_env()
    assert env["PATH"] == "/usr/bin:/bin:/usr/sbin:/sbin"
    assert env["HOME"] == "/home/runner"
    assert "SYSTEMROOT" not in env


def test_explicit_extra_still_wins(windows: None) -> None:
    assert base_env({"PATH": "/opt/custom"})["PATH"] == "/opt/custom"

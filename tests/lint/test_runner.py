# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from tofusoup.lint.models import LintSuite, OpenTofuSpec, ProviderSpec
from tofusoup.lint.runner import LintRunError, run_suite


def test_native_suite_requires_opentofu_before_starting_provider(monkeypatch, tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    suite = LintSuite(
        version=1,
        provider=ProviderSpec(source="registry.opentofu.org/example/demo", version="1.2.3"),
        cases=(),
        opentofu=OpenTofuSpec(fixture=fixture, lint="all"),
    )
    called = False

    async def direct_lane(*args):
        nonlocal called
        called = True

    monkeypatch.setattr("tofusoup.lint.runner.run_direct_suite", direct_lane)

    with pytest.raises(LintRunError, match="pass --opentofu PATH"):
        run_suite(suite, tmp_path / "provider", None)

    assert called is False


def test_opentofu_lane_does_not_start_direct_provider(monkeypatch, tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    suite = LintSuite(
        version=1,
        provider=ProviderSpec(source="registry.opentofu.org/example/demo", version="1.2.3"),
        cases=(),
        opentofu=OpenTofuSpec(fixture=fixture, lint="all"),
    )
    called = False

    async def direct_lane(*args):
        nonlocal called
        called = True

    monkeypatch.setattr("tofusoup.lint.runner.run_direct_suite", direct_lane)
    monkeypatch.setattr(
        "tofusoup.lint.runner.run_opentofu",
        lambda *args: SimpleNamespace(valid=True, diagnostics=()),
    )

    assert "lane" in inspect.signature(run_suite).parameters
    result = run_suite(suite, tmp_path / "provider", tmp_path / "tofu", lane="opentofu")

    assert called is False
    assert result.direct is None
    assert result.opentofu is not None

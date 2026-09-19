# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib
import json
from types import SimpleNamespace

from click.testing import CliRunner

from tofusoup.cli import main_cli


def test_lint_command_is_listed_and_describes_both_lanes() -> None:
    result = CliRunner().invoke(main_cli, ["lint", "--help"])

    assert result.exit_code == 0, result.output
    assert "Direct provider validation" in result.output
    assert "OpenTofu native linting" in result.output
    assert "--provider" in result.output
    assert "--opentofu" in result.output


def test_lint_command_renders_separate_direct_and_opentofu_results(monkeypatch, tmp_path) -> None:
    cli = importlib.import_module("tofusoup.lint.cli")
    suite = tmp_path / "lint.soup.toml"
    suite.write_text(
        """version = 1

[provider]
source = "registry.opentofu.org/example/demo"
version = "1.2.3"
""",
        encoding="utf-8",
    )
    provider = tmp_path / "terraform-provider-demo"
    provider.write_text("provider", encoding="utf-8")
    tofu = tmp_path / "tofu"
    tofu.write_text("tofu", encoding="utf-8")
    expected = SimpleNamespace(
        direct=SimpleNamespace(
            cases=(
                SimpleNamespace(
                    kind="resource",
                    type_name="example_thing",
                    diagnostics=(
                        SimpleNamespace(severity="warning", summary="Example lint", detail="detail"),
                    ),
                ),
            )
        ),
        opentofu=SimpleNamespace(valid=True, diagnostics=()),
        failure_messages=(),
    )

    assert getattr(cli, "run_suite", None) is not None
    monkeypatch.setattr(cli, "run_suite", lambda *args, **kwargs: expected)
    result = CliRunner().invoke(
        cli.lint_cli,
        [str(suite), "--provider", str(provider), "--opentofu", str(tofu)],
    )

    assert result.exit_code == 0, result.output
    assert "Direct provider validation: 1/1 cases" in result.output
    assert "OpenTofu native linting: valid" in result.output
    assert "OpenTofu coverage is separate from direct provider coverage" in result.output


def test_lint_command_json_has_stable_lane_keys(monkeypatch, tmp_path) -> None:
    cli = importlib.import_module("tofusoup.lint.cli")
    suite = tmp_path / "lint.soup.toml"
    suite.write_text(
        """version = 1

[provider]
source = "registry.opentofu.org/example/demo"
version = "1.2.3"
""",
        encoding="utf-8",
    )
    provider = tmp_path / "terraform-provider-demo"
    provider.write_text("provider", encoding="utf-8")
    expected = SimpleNamespace(direct=SimpleNamespace(cases=()), opentofu=None, failure_messages=())

    assert getattr(cli, "run_suite", None) is not None
    monkeypatch.setattr(cli, "run_suite", lambda *args, **kwargs: expected)
    result = CliRunner().invoke(cli.lint_cli, [str(suite), "--provider", str(provider), "--json"])

    assert result.exit_code == 0, result.output
    assert set(json.loads(result.output)) == {"direct", "opentofu", "version"}


def test_lint_command_fails_when_direct_contract_has_failures(monkeypatch, tmp_path) -> None:
    cli = importlib.import_module("tofusoup.lint.cli")
    suite = tmp_path / "lint.soup.toml"
    suite.write_text(
        """version = 1

[provider]
source = "registry.opentofu.org/example/demo"
version = "1.2.3"
""",
        encoding="utf-8",
    )
    provider = tmp_path / "terraform-provider-demo"
    provider.write_text("provider", encoding="utf-8")
    expected = SimpleNamespace(
        direct=SimpleNamespace(cases=(), failures=("resource example_thing returned an error diagnostic",)),
        opentofu=None,
        failure_messages=("resource example_thing returned an error diagnostic",),
    )

    monkeypatch.setattr(cli, "run_suite", lambda *args, **kwargs: expected)
    result = CliRunner().invoke(cli.lint_cli, [str(suite), "--provider", str(provider)])

    assert result.exit_code == 1
    assert "resource example_thing returned an error diagnostic" in result.output

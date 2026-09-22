# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_provider_linting_docs_show_only_public_commands() -> None:
    guide = (ROOT / "docs/guides/provider-linting.md").read_text(encoding="utf-8")
    reference = (ROOT / "docs/reference/cli.md").read_text(encoding="utf-8")

    assert "soup lint" in guide
    assert "--provider" in guide
    assert "--opentofu" in guide
    assert "provider.version" in guide
    assert "run-provider-linting-rpcs.py" not in guide
    assert "OpenTofu coverage is separate" in guide
    assert "### soup lint" in reference


def test_provider_linting_docs_explain_direct_only_invocation() -> None:
    guide = (ROOT / "docs/guides/provider-linting.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs/architecture/08-provider-linting.md").read_text(encoding="utf-8")
    reference = (ROOT / "docs/reference/cli.md").read_text(encoding="utf-8")

    assert "omit `--opentofu`, select `--lane direct`" in guide
    assert "omit `--opentofu`, select `--lane direct`" in architecture
    lint_commands = [line for line in reference.splitlines() if line.startswith("$ soup lint ")]
    assert lint_commands
    assert all("--opentofu" in command or "--lane direct" in command for command in lint_commands)


def test_architecture_diagram_has_direct_and_experimental_validation_lanes() -> None:
    architecture = (ROOT / "docs/architecture/08-provider-linting.md").read_text(encoding="utf-8")
    navigation = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "Direct tfprotov6 lane" in architecture
    assert "OpenTofu experimental lint validation lane" in architecture
    assert "provider version" in architecture
    assert "Provider linting: guides/provider-linting.md" in navigation


def test_public_lint_docs_do_not_claim_native_provider_linting() -> None:
    public_docs = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "docs/guides/provider-linting.md",
            "docs/architecture/08-provider-linting.md",
            "docs/reference/cli.md",
        )
    )

    assert "OpenTofu experimental lint validation lane" in public_docs
    assert "native lint" not in public_docs.lower()
    assert "beta validation" not in public_docs.lower()


def test_experimental_lane_wording_is_prepared_as_0_8_2() -> None:
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "0.8.2"

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    section = changelog.partition("## [0.8.2] - 2026-09-22")[2].partition("\n## [")[0]
    assert "OpenTofu experimental lint validation lane" in section
    assert "native linting" in section

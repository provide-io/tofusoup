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

    assert "omit `--opentofu`, select `--lane direct`" in guide
    assert "omit `--opentofu`, select `--lane direct`" in architecture


def test_architecture_diagram_has_direct_and_native_lanes() -> None:
    architecture = (ROOT / "docs/architecture/08-provider-linting.md").read_text(encoding="utf-8")
    navigation = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "Direct tfprotov6 lane" in architecture
    assert "OpenTofu native lane" in architecture
    assert "provider version" in architecture
    assert "Provider linting: guides/provider-linting.md" in navigation

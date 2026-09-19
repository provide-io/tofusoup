# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib
from pathlib import Path

import pytest


def write_suite(path: Path, content: str) -> Path:
    suite_path = path / "lint.soup.toml"
    suite_path.write_text(content, encoding="utf-8")
    return suite_path


def test_load_suite_parses_direct_and_native_lanes(tmp_path: Path) -> None:
    try:
        models = importlib.import_module("tofusoup.lint.models")
        suite_module = importlib.import_module("tofusoup.lint.suite")
    except ModuleNotFoundError:
        pytest.fail("provider lint suite modules have not been implemented")

    (tmp_path / "native").mkdir()
    suite_path = write_suite(
        tmp_path,
        """version = 1

[provider]
source = "registry.opentofu.org/example/demo"

[provider.environment]
EXAMPLE_LINT = "example:all"

[[case]]
kind = "resource"
type_name = "example_thing"
config = { insecure = true }
expect = [{ severity = "warning", summary = "Insecure thing" }]

[opentofu]
fixture = "native"
lint = "all"
""",
    )

    suite = suite_module.load_suite(suite_path)

    assert suite.version == 1
    assert suite.provider.source == "registry.opentofu.org/example/demo"
    assert suite.provider.environment == {"EXAMPLE_LINT": "example:all"}
    assert suite.cases[0].kind is models.ComponentKind.RESOURCE
    assert suite.cases[0].type_name == "example_thing"
    assert suite.opentofu is not None
    assert suite.opentofu.fixture == tmp_path / "native"


def test_load_suite_rejects_type_name_for_provider_case(tmp_path: Path) -> None:
    try:
        suite_module = importlib.import_module("tofusoup.lint.suite")
    except ModuleNotFoundError:
        pytest.fail("provider lint suite modules have not been implemented")

    suite_path = write_suite(
        tmp_path,
        """version = 1

[provider]
source = "registry.opentofu.org/example/demo"

[[case]]
kind = "provider"
type_name = "wrong"
config = {}
""",
    )

    with pytest.raises(suite_module.SuiteError, match="provider cases must not declare type_name"):
        suite_module.load_suite(suite_path)

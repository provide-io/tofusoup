# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib
import json
from pathlib import Path
import stat

import pytest

from tofusoup.lint.models import LintSuite, OpenTofuSpec, ProviderSpec


def executable(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def fake_tofu(path: Path, log_path: Path) -> Path:
    return executable(
        path,
        f"""#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

log = Path({str(log_path)!r})
entries = json.loads(log.read_text()) if log.exists() else []
entries.append({{
    "args": sys.argv[1:],
    "cwd": os.getcwd(),
    "cli_config_exists": Path(os.environ["TF_CLI_CONFIG_FILE"]).is_file(),
    "data_dir_exists": Path(os.environ["TF_DATA_DIR"]).is_dir(),
    "cli_config": Path(os.environ["TF_CLI_CONFIG_FILE"]).read_text(),
    "example_lint": os.environ["EXAMPLE_LINT"],
}})
log.write_text(json.dumps(entries))
if sys.argv[1] == "validate":
    print(json.dumps({{"valid": True, "diagnostics": []}}))
""",
    )


def test_native_runner_installs_binary_and_invokes_lint(tmp_path: Path) -> None:
    try:
        opentofu = importlib.import_module("tofusoup.lint.opentofu")
    except ModuleNotFoundError:
        pytest.fail("native OpenTofu lint runner has not been implemented")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "main.tf").write_text("terraform {}\n", encoding="utf-8")
    provider = executable(tmp_path / "terraform-provider-demo", "#!/bin/sh\n")
    log_path = tmp_path / "tofu-log.json"
    tofu = fake_tofu(tmp_path / "tofu", log_path)
    suite = LintSuite(
        version=1,
        provider=ProviderSpec(
            source="registry.opentofu.org/example/demo",
            version="1.2.3",
            environment={"EXAMPLE_LINT": "example:all"},
        ),
        cases=(),
        opentofu=OpenTofuSpec(fixture=fixture, lint="all"),
    )

    result = opentofu.run_opentofu(suite, provider, tofu)

    assert result.valid is True
    assert result.diagnostics == ()
    entries = json.loads(log_path.read_text(encoding="utf-8"))
    assert [entry["args"] for entry in entries] == [
        ["init", "-backend=false", "-input=false", "-no-color"],
        ["validate", "-json", "-no-color", "-lint=all"],
    ]
    assert all(entry["example_lint"] == "example:all" for entry in entries)
    assert all(entry["cli_config_exists"] for entry in entries)
    assert all(entry["data_dir_exists"] for entry in entries)
    assert all("registry.opentofu.org/example/demo" in entry["cli_config"] for entry in entries)
    assert not (fixture / ".terraform").exists()

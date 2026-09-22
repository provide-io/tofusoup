# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from tofusoup.lint.models import LintSuite, OpenTofuSpec, ProviderSpec


def executable(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def fake_tofu(path: Path, log_path: Path) -> Path:
    script = f"""import json
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
"""
    if os.name != "nt":
        return executable(path, f"#!{sys.executable}\n{script}")
    python_script = path.with_suffix(".py")
    python_script.write_text(script, encoding="utf-8")
    launcher = path.with_suffix(".cmd")
    launcher.write_text(f'@"{sys.executable}" "{python_script}" %*\n', encoding="utf-8")
    return launcher


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


def test_native_runner_resolves_relative_executable_before_changing_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opentofu = importlib.import_module("tofusoup.lint.opentofu")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "main.tf").write_text("terraform {}\n", encoding="utf-8")
    provider = executable(tmp_path / "terraform-provider-demo", "#!/bin/sh\n")
    log_path = tmp_path / "tofu-log.json"
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    tofu = fake_tofu(tools_dir / "tofu", log_path)
    suite = LintSuite(
        version=1,
        provider=ProviderSpec(
            source="registry.opentofu.org/example/demo",
            version="1.2.3",
            environment={"EXAMPLE_LINT": "example:all", "PATH": ""},
        ),
        cases=(),
        opentofu=OpenTofuSpec(fixture=fixture, lint="all"),
    )
    monkeypatch.chdir(tmp_path)

    result = opentofu.run_opentofu(suite, provider, Path("tools") / tofu.name)

    assert result.valid is True
    assert len(json.loads(log_path.read_text(encoding="utf-8"))) == 2


def test_native_runner_resolves_executable_from_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    opentofu = importlib.import_module("tofusoup.lint.opentofu")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "main.tf").write_text("terraform {}\n", encoding="utf-8")
    provider = executable(tmp_path / "terraform-provider-demo", "#!/bin/sh\n")
    log_path = tmp_path / "tofu-log.json"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_tofu(bin_dir / "tofu", log_path)
    suite = LintSuite(
        version=1,
        provider=ProviderSpec(
            source="registry.opentofu.org/example/demo",
            version="1.2.3",
            environment={"EXAMPLE_LINT": "example:all", "PATH": ""},
        ),
        cases=(),
        opentofu=OpenTofuSpec(fixture=fixture, lint="all"),
    )
    monkeypatch.chdir(tmp_path / "fixture")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    result = opentofu.run_opentofu(suite, provider, Path("tofu"))

    assert result.valid is True
    assert len(json.loads(log_path.read_text(encoding="utf-8"))) == 2


def test_native_runner_wraps_process_start_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    opentofu = importlib.import_module("tofusoup.lint.opentofu")

    def fail_to_start(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise PermissionError("permission denied")

    monkeypatch.setattr(opentofu.subprocess, "run", fail_to_start)

    with pytest.raises(opentofu.OpenTofuError, match="OpenTofu init could not start: permission denied"):
        opentofu._run(["tofu", "init"], tmp_path, {}, "init")

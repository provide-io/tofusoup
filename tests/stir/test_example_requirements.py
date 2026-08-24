#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""An example directory can declare what it needs before stir runs it.

The point is the distinction between "this failed" and "this cannot run here".
Four of the provider's examples use blocks OpenTofu has no concept of; running
them under tofu produced errors indistinguishable from real defects, and was the
unexplained gap between 48 examples and the 44 that ever passed.
"""

from pathlib import Path

import pytest

from tofusoup.stir.requirements import Requirements, load_requirements

ACTION = """[requirements]
opentofu = false
reason = "OpenTofu rejects `action` blocks: Unsupported block type"
"""

STORE = """[requirements]
opentofu = false
init_flags = ["-enable-pluggable-state-storage-experiment"]
reason = "state_store is experimental in Terraform and unsupported in OpenTofu"
"""

SECRET = """[requirements]
env = ["PYVIDER_PRIVATE_STATE_SHARED_SECRET"]
reason = "encrypted private state needs a configured shared secret"
"""


@pytest.mark.unit
def test_a_directory_without_sidecars_requires_nothing(tmp_path: Path) -> None:
    (tmp_path / "example.tf").write_text('resource "x" "y" {}')

    requirements = load_requirements(tmp_path)

    assert requirements == Requirements()
    assert requirements.skip_reason("tofu") is None


@pytest.mark.unit
def test_opentofu_incompatible_examples_skip_under_tofu_and_run_under_terraform(
    tmp_path: Path,
) -> None:
    (tmp_path / "example.meta.toml").write_text(ACTION)

    requirements = load_requirements(tmp_path)

    assert "Unsupported block type" in (requirements.skip_reason("tofu") or "")
    assert requirements.skip_reason("/usr/local/bin/terraform") is None


@pytest.mark.unit
def test_declared_init_flags_are_collected(tmp_path: Path) -> None:
    (tmp_path / "example.meta.toml").write_text(STORE)

    assert load_requirements(tmp_path).init_flags == ("-enable-pluggable-state-storage-experiment",)


@pytest.mark.unit
def test_a_missing_environment_variable_is_a_skip_not_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "example.meta.toml").write_text(SECRET)
    monkeypatch.delenv("PYVIDER_PRIVATE_STATE_SHARED_SECRET", raising=False)

    reason = load_requirements(tmp_path).skip_reason("terraform")

    assert reason is not None
    assert "PYVIDER_PRIVATE_STATE_SHARED_SECRET" in reason


@pytest.mark.unit
def test_a_satisfied_environment_variable_does_not_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "example.meta.toml").write_text(SECRET)
    monkeypatch.setenv("PYVIDER_PRIVATE_STATE_SHARED_SECRET", "s3cret")

    assert load_requirements(tmp_path).skip_reason("terraform") is None


@pytest.mark.unit
def test_a_directory_takes_the_union_of_its_examples(tmp_path: Path) -> None:
    """A component directory holds several examples and is run as a unit."""
    (tmp_path / "basic.meta.toml").write_text(SECRET)
    (tmp_path / "advanced.meta.toml").write_text(STORE)

    requirements = load_requirements(tmp_path)

    assert requirements.opentofu is False
    assert requirements.env == ("PYVIDER_PRIVATE_STATE_SHARED_SECRET",)
    assert requirements.init_flags == ("-enable-pluggable-state-storage-experiment",)


@pytest.mark.unit
def test_a_malformed_sidecar_never_fails_the_run(tmp_path: Path) -> None:
    (tmp_path / "example.meta.toml").write_text("this = is not [ toml")

    assert load_requirements(tmp_path) == Requirements()


@pytest.mark.unit
def test_terraform_aliased_to_tofu_is_detected_by_binary_name(tmp_path: Path) -> None:
    """`terraform` is commonly a symlink or alias to `tofu`."""
    (tmp_path / "example.meta.toml").write_text(ACTION)
    requirements = load_requirements(tmp_path)

    assert requirements.skip_reason("/opt/homebrew/bin/tofu") is not None
    assert requirements.skip_reason("tofu.exe") is not None

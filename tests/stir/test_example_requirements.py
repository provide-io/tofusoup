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


NON_CONVERGING = """[requirements]
converges = false
reason = "the API stamps a new timestamp on every read"
"""


@pytest.mark.unit
def test_convergence_is_expected_unless_a_sidecar_opts_out(tmp_path: Path) -> None:
    """Re-planning after apply should be empty; a directory says so when it is not."""
    (tmp_path / "example.tf").write_text('resource "x" "y" {}')

    assert load_requirements(tmp_path).converges is True

    (tmp_path / "example.meta.toml").write_text(NON_CONVERGING)

    assert load_requirements(tmp_path).converges is False


@pytest.mark.unit
def test_one_non_converging_example_opts_out_the_whole_directory(tmp_path: Path) -> None:
    """Sidecars merge, and the directory is planned as a whole."""
    (tmp_path / "a.meta.toml").write_text(NON_CONVERGING)
    (tmp_path / "b.meta.toml").write_text('[requirements]\nreason = "nothing special"\n')

    assert load_requirements(tmp_path).converges is False


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


NETWORK = """[requirements]
network = ["httpbin.org"]
reason = "the examples call the live httpbin.org service"
"""


@pytest.mark.unit
def test_network_examples_run_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "example.meta.toml").write_text(NETWORK)
    monkeypatch.delenv("TOFUSOUP_OFFLINE", raising=False)

    assert load_requirements(tmp_path).skip_reason("terraform") is None


@pytest.mark.unit
def test_offline_skips_examples_that_reach_the_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A third party's downtime is not a defect in the provider."""
    (tmp_path / "example.meta.toml").write_text(NETWORK)
    monkeypatch.setenv("TOFUSOUP_OFFLINE", "1")

    reason = load_requirements(tmp_path).skip_reason("terraform")

    assert reason is not None
    assert "httpbin.org" in reason


@pytest.mark.unit
def test_offline_does_not_skip_examples_that_need_no_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "example.tf").write_text('resource "x" "y" {}')
    monkeypatch.setenv("TOFUSOUP_OFFLINE", "true")

    assert load_requirements(tmp_path).skip_reason("terraform") is None


@pytest.mark.unit
def test_an_explicit_allow_network_overrides_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "example.meta.toml").write_text(NETWORK)
    monkeypatch.setenv("TOFUSOUP_OFFLINE", "1")

    assert load_requirements(tmp_path).skip_reason("terraform", allow_network=True) is None


WRITE_ONLY = """[requirements]
opentofu_min = "1.11.0"
reason = "write-only attributes are not understood before OpenTofu 1.11"
"""


@pytest.mark.unit
def test_a_version_floor_skips_an_older_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The case this exists for: pyvider_secret_note on OpenTofu 1.10.6.

    The provider nulls a write-only attribute, which is correct, but 1.10.6 has
    no concept of one and enforces the ordinary rule that a planned value must
    equal its config value -- so it reports "Provider produced invalid plan" and
    blames the provider for behaving properly.
    """
    from tofusoup.stir import requirements as mod

    (tmp_path / "example.meta.toml").write_text(WRITE_ONLY)
    mod.binary_version.cache_clear()
    monkeypatch.setattr(mod, "binary_version", lambda _cmd: "1.10.6")

    reason = load_requirements(tmp_path).skip_reason("tofu")

    assert reason is not None
    assert "1.11.0" in reason and "1.10.6" in reason


@pytest.mark.unit
def test_a_version_floor_permits_a_newer_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tofusoup.stir import requirements as mod

    (tmp_path / "example.meta.toml").write_text(WRITE_ONLY)
    monkeypatch.setattr(mod, "binary_version", lambda _cmd: "1.12.5")

    assert load_requirements(tmp_path).skip_reason("tofu") is None


@pytest.mark.unit
def test_an_opentofu_floor_does_not_gate_terraform(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The two implementations version independently."""
    from tofusoup.stir import requirements as mod

    (tmp_path / "example.meta.toml").write_text(WRITE_ONLY)
    monkeypatch.setattr(mod, "binary_version", lambda _cmd: "1.5.0")

    assert load_requirements(tmp_path).skip_reason("/usr/bin/terraform") is None


@pytest.mark.unit
def test_an_unreadable_version_never_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Refusing to run over a version we could not read would be an obstacle."""
    from tofusoup.stir import requirements as mod

    (tmp_path / "example.meta.toml").write_text(WRITE_ONLY)
    monkeypatch.setattr(mod, "binary_version", lambda _cmd: "")

    assert load_requirements(tmp_path).skip_reason("tofu") is None


@pytest.mark.unit
def test_the_highest_floor_in_a_directory_wins(tmp_path: Path) -> None:
    (tmp_path / "a.meta.toml").write_text('[requirements]\nopentofu_min = "1.11.0"\n')
    (tmp_path / "b.meta.toml").write_text('[requirements]\nopentofu_min = "1.9.0"\n')

    assert load_requirements(tmp_path).opentofu_min == "1.11.0"


@pytest.mark.unit
def test_version_comparison_is_numeric_not_lexical(tmp_path: Path) -> None:
    """ "1.9.0" must not sort above "1.11.0"."""
    from tofusoup.stir.requirements import _parse

    assert _parse("1.9.0") < _parse("1.11.0")
    assert _parse("v1.11.0") == _parse("1.11.0")
    assert _parse("1.11.0-beta1") == _parse("1.11.0")

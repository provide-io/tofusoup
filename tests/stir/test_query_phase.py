#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""List resources are only reachable through `terraform query`.

Nothing else in the lifecycle touches one. `apply` does not evaluate a `list`
block, so a provider can ship a list resource that Terraform refuses on the
first query -- for a missing identity schema, say -- and still pass init,
apply, converge and destroy here. That is a gap the lifecycle cannot close by
running its existing phases more carefully.

`terraform query` reads `*.tfquery.hcl` and arrived in Terraform 1.14. OpenTofu
has no such command at any version, so a directory carrying query files runs
the rest of its lifecycle there and this phase stands aside rather than failing
it.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from tofusoup.stir.config import _find_tf_command
from tofusoup.stir.display import test_statuses
from tofusoup.stir.executor import _query_rc
from tofusoup.stir.requirements import (
    Requirements,
    has_experiments,
    load_requirements,
    supports_query,
)

MODULE = "tofusoup.stir.executor"
REQUIREMENTS = "tofusoup.stir.requirements"


@pytest.fixture(autouse=True)
def _status_row() -> None:
    test_statuses["example"] = {}
    yield
    test_statuses.pop("example", None)


def _terraform_result(returncode: int) -> tuple[int, str, None, None, None, None]:
    return (returncode, "", None, None, None, None)


def _with_query_file(directory: Path) -> Path:
    (directory / "list.tfquery.hcl").write_text('list "acme_widget" "all" {}\n')
    return directory


@pytest.mark.unit
class TestChoosingTheBinary:
    """The search order prefers OpenTofu, which cannot query."""

    def test_an_explicit_choice_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TOFUSOUP_TF_COMMAND", "terraform")
        with patch("tofusoup.stir.config.shutil.which", return_value="/usr/bin/terraform"):
            assert _find_tf_command() == "/usr/bin/terraform"

    def test_a_name_that_is_not_on_path_is_reported_as_asked_for(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Falling back to tofu here would run the opposite of what was asked."""
        monkeypatch.setenv("TOFUSOUP_TF_COMMAND", "terraform")
        with patch("tofusoup.stir.config.shutil.which", return_value=None):
            assert _find_tf_command() == "terraform"

    def test_without_a_choice_the_search_order_stands(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TOFUSOUP_TF_COMMAND", raising=False)
        monkeypatch.delenv("TOFU_CLI_PATH", raising=False)
        with patch("tofusoup.stir.config.shutil.which", side_effect=["/usr/bin/tofu", None]):
            assert _find_tf_command() == "/usr/bin/tofu"


@pytest.mark.unit
class TestWhichBuildsHaveExperiments:
    """Terraform compiles experiments into alpha and dev builds only.

    A stable release refuses the opt-in flag rather than ignoring it, so an
    example that needs one cannot run there at all:

        Error: Cannot use -enable-pluggable-state-storage-experiment flag
        without experiments enabled
    """

    def test_an_alpha_build_does(self) -> None:
        with patch(f"{REQUIREMENTS}.binary_version", return_value="1.17.0-alpha20260827"):
            assert has_experiments("terraform") is True

    def test_a_stable_release_does_not(self) -> None:
        with patch(f"{REQUIREMENTS}.binary_version", return_value="1.16.1"):
            assert has_experiments("terraform") is False

    def test_an_example_needing_one_is_skipped_with_its_reason(self) -> None:
        requirements = Requirements(experiments=True, reason="state_store is experimental")
        with patch(f"{REQUIREMENTS}.binary_version", return_value="1.16.1"):
            reason = requirements.skip_reason("terraform")

        assert reason is not None
        assert "experiments" in reason
        assert "state_store is experimental" in reason

    def test_the_sidecar_key_survives_the_loader(self, tmp_path: Path) -> None:
        """The merge reads a fixed set of keys, so a new one has to be added to it.

        Constructing `Requirements` directly cannot show that: the field exists
        either way. Only the path a real sidecar takes does.
        """
        (tmp_path / "example.meta.toml").write_text(
            '[requirements]\nexperiments = true\nreason = "needs an alpha"\n'
        )

        assert load_requirements(tmp_path).experiments is True

    def test_an_example_needing_one_runs_on_an_alpha(self) -> None:
        requirements = Requirements(experiments=True)
        with patch(f"{REQUIREMENTS}.binary_version", return_value="1.17.0-alpha20260827"):
            assert requirements.skip_reason("terraform") is None


@pytest.mark.unit
class TestWhichBinariesCanQuery:
    def test_opentofu_cannot(self) -> None:
        assert supports_query("tofu") is False

    def test_terraform_at_the_floor_can(self) -> None:
        with patch(f"{REQUIREMENTS}.binary_version", return_value="1.14.0"):
            assert supports_query("terraform") is True

    def test_terraform_below_the_floor_cannot(self) -> None:
        with patch(f"{REQUIREMENTS}.binary_version", return_value="1.13.9"):
            assert supports_query("terraform") is False

    def test_terraform_aliased_to_tofu_is_caught_by_its_version(self) -> None:
        """`terraform` is frequently an alias for `tofu`, which reports 1.x.

        The name check cannot see through the alias; the version can, because
        OpenTofu's own numbering has not reached Terraform's query floor.
        """
        with patch(f"{REQUIREMENTS}.binary_version", return_value="1.12.6"):
            assert supports_query("terraform") is False

    def test_a_version_that_will_not_say_is_treated_as_unable(self) -> None:
        """Unlike a floor check, guessing wrong here costs a hard failure.

        A skipped directory is legible; `terraform query` against a binary
        without the command is an error that looks like the example's fault.
        """
        with patch(f"{REQUIREMENTS}.binary_version", return_value=""):
            assert supports_query("terraform") is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestTheQueryPhase:
    async def test_a_directory_with_no_query_files_is_not_queried(self, tmp_path: Path) -> None:
        run = AsyncMock(return_value=_terraform_result(0))
        with patch(f"{MODULE}.run_terraform_command", new=run):
            assert await _query_rc(tmp_path, "example", None) == 0

        run.assert_not_awaited()

    async def test_query_files_are_left_alone_on_a_binary_that_cannot_query(self, tmp_path: Path) -> None:
        run = AsyncMock(return_value=_terraform_result(0))
        _with_query_file(tmp_path)
        with (
            patch(f"{MODULE}.run_terraform_command", new=run),
            patch(f"{MODULE}.supports_query", return_value=False),
        ):
            assert await _query_rc(tmp_path, "example", None) == 0

        run.assert_not_awaited()

    async def test_a_successful_query_reports_zero(self, tmp_path: Path) -> None:
        _with_query_file(tmp_path)
        with (
            patch(f"{MODULE}.run_terraform_command", new=AsyncMock(return_value=_terraform_result(0))),
            patch(f"{MODULE}.supports_query", return_value=True),
        ):
            assert await _query_rc(tmp_path, "example", None) == 0

    async def test_a_failed_query_fails_the_directory(self, tmp_path: Path) -> None:
        """The identity-schema refusal reaches stir exactly here, and nowhere else."""
        _with_query_file(tmp_path)
        with (
            patch(f"{MODULE}.run_terraform_command", new=AsyncMock(return_value=_terraform_result(1))),
            patch(f"{MODULE}.supports_query", return_value=True),
        ):
            assert await _query_rc(tmp_path, "example", None) == 1

    async def test_the_command_is_the_one_terraform_documents(self, tmp_path: Path) -> None:
        """`query` takes no `-input`; passing one is an error, not a no-op."""
        run = AsyncMock(return_value=_terraform_result(0))
        _with_query_file(tmp_path)
        with (
            patch(f"{MODULE}.run_terraform_command", new=run),
            patch(f"{MODULE}.supports_query", return_value=True),
        ):
            await _query_rc(tmp_path, "example", None)

        assert run.await_args.args[1] == ["query", "-no-color"]


# 🥣🔚

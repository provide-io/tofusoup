#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""A directory that applied cleanly should have nothing left to plan.

`apply` returning 0 proves the plan could be carried out, not that the provider
planned everything it then wrote. The re-plan is what separates the two.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from tofusoup.stir.display import test_statuses
from tofusoup.stir.executor import _convergence_rc

MODULE = "tofusoup.stir.executor"


@pytest.fixture(autouse=True)
def _status_row() -> None:
    """The phase display is global state the executor writes progress into."""
    test_statuses["example"] = {}
    yield
    test_statuses.pop("example", None)


def _terraform_result(returncode: int) -> tuple[int, str, None, None, None, None]:
    """run_terraform_command's six-tuple, of which only the return code matters here."""
    return (returncode, "", None, None, None, None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_directory_with_nothing_pending_converges(tmp_path: Path) -> None:
    with patch(f"{MODULE}.run_terraform_command", new=AsyncMock(return_value=_terraform_result(0))):
        assert await _convergence_rc(tmp_path, "example", None, converges=True) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_changes_still_pending_after_apply_are_reported(tmp_path: Path) -> None:
    """Exit code 2 is terraform's "changes pending", and the whole point of this check."""
    with patch(f"{MODULE}.run_terraform_command", new=AsyncMock(return_value=_terraform_result(2))):
        assert await _convergence_rc(tmp_path, "example", None, converges=True) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_plan_that_errors_is_not_reported_as_converged(tmp_path: Path) -> None:
    with patch(f"{MODULE}.run_terraform_command", new=AsyncMock(return_value=_terraform_result(1))):
        assert await _convergence_rc(tmp_path, "example", None, converges=True) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_an_opted_out_directory_is_never_re_planned(tmp_path: Path) -> None:
    """`converges = false` should cost nothing, not run a plan and ignore it."""
    command = AsyncMock(return_value=_terraform_result(2))

    with patch(f"{MODULE}.run_terraform_command", new=command):
        assert await _convergence_rc(tmp_path, "example", None, converges=False) == 0

    command.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_the_re_plan_is_non_interactive_and_asks_for_the_detailed_code(
    tmp_path: Path,
) -> None:
    """Without -detailed-exitcode a plan with pending changes still exits 0."""
    command = AsyncMock(return_value=_terraform_result(0))

    with patch(f"{MODULE}.run_terraform_command", new=command):
        await _convergence_rc(tmp_path, "example", None, converges=True)

    args = command.await_args.args[1]
    assert args[0] == "plan"
    assert "-detailed-exitcode" in args
    assert "-input=false" in args


# 🍲🔁🔚

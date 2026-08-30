#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""A directory that will not tear down has not passed.

`destroy`'s exit code was discarded, so a teardown that failed still reported
PASS -- leaving infrastructure behind and the next run starting from a state
this one was supposed to have emptied.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from tofusoup.stir.display import test_statuses
from tofusoup.stir.executor import _destroy_rc, run_test_lifecycle

MODULE = "tofusoup.stir.executor"


@pytest.fixture(autouse=True)
def _status_row() -> None:
    test_statuses["example"] = {}
    yield
    test_statuses.pop("example", None)


def _result(returncode: int) -> tuple[int, str, None, None, None, None]:
    """run_terraform_command's six-tuple; only the return code matters here."""
    return (returncode, "", None, None, None, None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_clean_teardown_reports_zero(tmp_path: Path) -> None:
    with patch(f"{MODULE}.run_terraform_command", new=AsyncMock(return_value=_result(0))):
        assert await _destroy_rc(tmp_path, "example", None, style="dim green") == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_failed_teardown_is_reported(tmp_path: Path) -> None:
    with patch(f"{MODULE}.run_terraform_command", new=AsyncMock(return_value=_result(1))):
        assert await _destroy_rc(tmp_path, "example", None, style="dim green") == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_the_teardown_is_non_interactive(tmp_path: Path) -> None:
    command = AsyncMock(return_value=_result(0))
    with patch(f"{MODULE}.run_terraform_command", new=command):
        await _destroy_rc(tmp_path, "example", None, style="dim green")

    args = command.await_args.args[1]
    assert args[0] == "destroy"
    assert "-auto-approve" in args
    assert "-input=false" in args


def _example_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "example"
    directory.mkdir()
    (directory / "main.tf").write_text('output "x" { value = 1 }\n', encoding="utf-8")
    return directory


async def _lifecycle_with(destroy_rc: int, tmp_path: Path):
    """Drive the whole lifecycle, failing only `destroy`."""
    directory = _example_dir(tmp_path)

    async def fake(_directory, args, **_kwargs):
        return _result(destroy_rc if args[0] == "destroy" else 0)

    runtime = AsyncMock()
    runtime.validate_ready = lambda: None
    with (
        patch(f"{MODULE}.run_terraform_command", new=fake),
        patch(f"{MODULE}.TF_COMMAND", "tofu"),
    ):
        return await run_test_lifecycle(directory, asyncio.Semaphore(1), runtime)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_everything_passing_still_passes(tmp_path: Path) -> None:
    """The ordinary path must be untouched by the destroy check."""
    result = await _lifecycle_with(0, tmp_path)
    assert result.success is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_directory_that_will_not_tear_down_fails(tmp_path: Path) -> None:
    """The regression: apply and converge succeed, destroy does not, result was PASS."""
    result = await _lifecycle_with(1, tmp_path)
    assert result.success is False, "a failed destroy must fail the test"


# 🍲💥🔚

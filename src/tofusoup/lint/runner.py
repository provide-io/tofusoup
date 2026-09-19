# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Orchestration for direct and OpenTofu provider lint suite lanes."""

import asyncio
from pathlib import Path

from attrs import define

from tofusoup.lint.direct import DirectSuiteResult, run_direct_suite
from tofusoup.lint.models import LintSuite
from tofusoup.lint.opentofu import OpenTofuResult, run_opentofu


class LintRunError(RuntimeError):
    """The requested lint lane cannot be run with the supplied options."""


@define(frozen=True)
class LintRunResult:
    """The independently reported direct and native lint results."""

    direct: DirectSuiteResult
    opentofu: OpenTofuResult | None


def run_suite(suite: LintSuite, provider: Path, tofu: Path | None) -> LintRunResult:
    """Run every lane declared by a lint suite."""
    if suite.opentofu is not None and tofu is None:
        raise LintRunError("this suite declares an OpenTofu lane; pass --opentofu PATH")
    direct = asyncio.run(run_direct_suite(suite, provider))
    if suite.opentofu is None:
        return LintRunResult(direct=direct, opentofu=None)
    return LintRunResult(direct=direct, opentofu=run_opentofu(suite, provider, tofu))

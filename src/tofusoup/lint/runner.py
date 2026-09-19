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

    direct: DirectSuiteResult | None
    opentofu: OpenTofuResult | None

    @property
    def failure_messages(self) -> tuple[str, ...]:
        """Contract failures that require a non-zero command exit."""
        failures = [] if self.direct is None else list(self.direct.failures)
        if self.opentofu is not None and not self.opentofu.valid:
            failures.append("OpenTofu validate reported an invalid configuration")
        return tuple(failures)


def run_suite(suite: LintSuite, provider: Path, tofu: Path | None, lane: str = "all") -> LintRunResult:
    """Run every lane declared by a lint suite."""
    if lane not in {"all", "direct", "opentofu"}:
        raise LintRunError(f"unknown lint lane: {lane}")
    if lane == "opentofu" and suite.opentofu is None:
        raise LintRunError("this suite does not declare an OpenTofu lane")
    wants_opentofu = lane in {"all", "opentofu"} and suite.opentofu is not None
    if wants_opentofu and tofu is None:
        raise LintRunError("this suite declares an OpenTofu lane; pass --opentofu PATH")
    direct = asyncio.run(run_direct_suite(suite, provider)) if lane in {"all", "direct"} else None
    opentofu = run_opentofu(suite, provider, tofu) if tofu is not None and wants_opentofu else None
    return LintRunResult(direct=direct, opentofu=opentofu)

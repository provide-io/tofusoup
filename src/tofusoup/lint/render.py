# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Stable terminal and JSON rendering for provider lint results."""

import json
from typing import Any

from tofusoup.lint.runner import LintRunResult


def _kind(value: Any) -> str:
    return getattr(value, "value", str(value))


def _diagnostic(value: Any) -> dict[str, str]:
    return {"severity": value.severity, "summary": value.summary, "detail": value.detail}


def result_json(result: LintRunResult) -> dict[str, Any]:
    """Convert a lint result to the public machine-readable schema."""
    return {
        "version": 1,
        "direct": None
        if result.direct is None
        else {
            "cases": [
                {
                    "kind": _kind(case.kind),
                    "type_name": case.type_name,
                    "diagnostics": [_diagnostic(diagnostic) for diagnostic in case.diagnostics],
                }
                for case in result.direct.cases
            ]
        },
        "opentofu": None
        if result.opentofu is None
        else {
            "valid": result.opentofu.valid,
            "diagnostics": [_diagnostic(diagnostic) for diagnostic in result.opentofu.diagnostics],
        },
    }


def render_json(result: LintRunResult) -> str:
    """Render a stable JSON document with direct and OpenTofu lane keys."""
    return json.dumps(result_json(result), sort_keys=True)


def render_terminal(result: LintRunResult) -> str:
    """Render direct and OpenTofu findings without conflating their coverage."""
    lines = []
    if result.direct is None:
        lines.append("Direct provider validation: not requested")
    else:
        lines.append(
            f"Direct provider validation: {len(result.direct.cases)}/{len(result.direct.cases)} cases"
        )
        for case in result.direct.cases:
            label = _kind(case.kind) if case.type_name is None else f"{_kind(case.kind)} {case.type_name}"
            if not case.diagnostics:
                lines.append(f"  ✓ {label}: no diagnostics")
            for diagnostic in case.diagnostics:
                lines.append(f"  {diagnostic.severity}: {label}: {diagnostic.summary}")
    if result.opentofu is None:
        lines.append("OpenTofu experimental lint validation: not requested")
    else:
        state = "valid" if result.opentofu.valid else "invalid"
        lines.append(f"OpenTofu experimental lint validation: {state}")
        for diagnostic in result.opentofu.diagnostics:
            lines.append(f"  {diagnostic.severity}: {diagnostic.summary}")
    lines.append("OpenTofu coverage is separate from direct provider coverage.")
    return "\n".join(lines)

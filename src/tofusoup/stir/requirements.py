#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""What an example directory needs before it can be run.

Examples are compiled out of `.plating` bundles, and a constrained one ships a
sidecar naming its requirements: `example.tf` is described by
`example.meta.toml`. Requirements are not one-dimensional -- a Terraform floor,
an OpenTofu incompatibility, an extra `init` flag, an environment variable,
network egress -- which is why they are declared rather than inferred from a
filename.

Before this, a directory that could not run here simply failed, and the run
reported a failure indistinguishable from a real defect. The four examples
OpenTofu cannot parse at all were quietly the difference between "48 examples"
and the 44 that ever passed.
"""

from __future__ import annotations

import os
from pathlib import Path
import tomllib

from attrs import define, field

#
# tofusoup/stir/requirements.py
#

METADATA_SUFFIX = ".meta.toml"


@define(frozen=True)
class Requirements:
    """Merged requirements for one example directory."""

    #: False when the configuration uses a block OpenTofu has no concept of.
    opentofu: bool = True
    #: Extra flags this directory needs at `init`, e.g. an experiment opt-in.
    init_flags: tuple[str, ...] = ()
    #: Environment variables that must be set for the example to work.
    env: tuple[str, ...] = ()
    #: Hosts the example reaches. Present so an air-gapped runner can opt out.
    network: tuple[str, ...] = ()
    #: Human-readable explanation, surfaced when a directory is skipped.
    reason: str = ""

    def skip_reason(self, tf_command: str, *, allow_network: bool = True) -> str | None:
        """Why this directory cannot run here, or None if it can.

        A skip is a statement about the runner, not about the configuration --
        so it carries the declared reason rather than a generic message.
        """
        if not self.opentofu and _is_opentofu(tf_command):
            return self.reason or "not supported by OpenTofu"

        missing = [name for name in self.env if not os.environ.get(name)]
        if missing:
            detail = ", ".join(missing)
            return f"{self.reason or 'missing required environment'}: {detail}"

        if self.network and not allow_network:
            return f"needs network access to {', '.join(self.network)}"

        return None


def _is_opentofu(tf_command: str) -> bool:
    """Whether the configured binary is OpenTofu rather than Terraform.

    Decided by name because that is all stir knows without paying for a
    subprocess per directory; `terraform` is frequently an alias for `tofu`, so
    a false negative here costs a confusing failure rather than a wrong skip.
    """
    return Path(tf_command).name.lower().startswith("tofu")


def _as_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list | tuple):
        return tuple(str(item) for item in value)
    return ()


@define
class _Merge:
    """Accumulator for the union of a directory's sidecars."""

    opentofu: bool = True
    init_flags: list[str] = field(factory=list)
    env: list[str] = field(factory=list)
    network: list[str] = field(factory=list)
    reasons: list[str] = field(factory=list)

    def absorb(self, block: dict[str, object]) -> None:
        if block.get("opentofu") is False:
            self.opentofu = False
        for key, target in (
            ("init_flags", self.init_flags),
            ("env", self.env),
            ("network", self.network),
        ):
            for item in _as_tuple(block.get(key)):
                if item not in target:
                    target.append(item)
        reason = block.get("reason")
        if isinstance(reason, str) and reason and reason not in self.reasons:
            self.reasons.append(reason)


def _read_block(sidecar: Path) -> dict[str, object] | None:
    """The [requirements] table of one sidecar, or None if it has none.

    Unreadable and malformed are both None. These describe an example; they are
    not a gate, and aborting a run over unparseable metadata trades a small
    problem for a larger one.
    """
    try:
        with sidecar.open("rb") as handle:
            parsed = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    block = parsed.get("requirements")
    return block if isinstance(block, dict) else None


def load_requirements(directory: Path) -> Requirements:
    """Merge every sidecar in a directory into one set of requirements.

    A compiled component directory can hold several examples and is run as a
    unit, so its requirements are the union: any example that cannot run under
    OpenTofu makes the directory unrunnable there, and every declared flag and
    variable is needed.
    """
    merged = _Merge()
    for sidecar in sorted(directory.glob(f"*{METADATA_SUFFIX}")):
        block = _read_block(sidecar)
        if block is not None:
            merged.absorb(block)

    return Requirements(
        opentofu=merged.opentofu,
        init_flags=tuple(merged.init_flags),
        env=tuple(merged.env),
        network=tuple(merged.network),
        reason="; ".join(merged.reasons),
    )


# 🍲📋🔚

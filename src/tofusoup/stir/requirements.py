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

from functools import lru_cache
import json
import os
from pathlib import Path
import subprocess
import tomllib

from attrs import define, field

from tofusoup.config.defaults import ENV_TOFUSOUP_OFFLINE

#
# tofusoup/stir/requirements.py
#

METADATA_SUFFIX = ".meta.toml"


@define(frozen=True)
class Requirements:
    """Merged requirements for one example directory."""

    #: False when the configuration uses a block OpenTofu has no concept of.
    opentofu: bool = True
    #: Lowest OpenTofu that can run this, e.g. "1.11.0" for write-only attributes.
    opentofu_min: str = ""
    #: Lowest Terraform that can run this.
    terraform_min: str = ""
    #: Extra flags this directory needs at `init`, e.g. an experiment opt-in.
    init_flags: tuple[str, ...] = ()
    #: Environment variables that must be set for the example to work.
    env: tuple[str, ...] = ()
    #: Hosts the example reaches. Present so an air-gapped runner can opt out.
    network: tuple[str, ...] = ()
    #: Human-readable explanation, surfaced when a directory is skipped.
    reason: str = ""

    def skip_reason(self, tf_command: str, *, allow_network: bool | None = None) -> str | None:
        """Why this directory cannot run here, or None if it can.

        A skip is a statement about the runner, not about the configuration --
        so it carries the declared reason rather than a generic message.
        """
        is_tofu = _is_opentofu(tf_command)
        if not self.opentofu and is_tofu:
            return self.reason or "not supported by OpenTofu"

        floor = self.opentofu_min if is_tofu else self.terraform_min
        if floor:
            found = binary_version(tf_command)
            name = "OpenTofu" if is_tofu else "Terraform"
            if found and _parse(found) < _parse(floor):
                detail = self.reason or "unsupported by this version"
                return f"needs {name} >= {floor}, found {found}: {detail}"

        missing = [name for name in self.env if not os.environ.get(name)]
        if missing:
            detail = ", ".join(missing)
            return f"{self.reason or 'missing required environment'}: {detail}"

        if allow_network is None:
            allow_network = not _truthy(os.environ.get(ENV_TOFUSOUP_OFFLINE))
        if self.network and not allow_network:
            return f"needs network access to {', '.join(self.network)}"

        return None


def _parse(version: str) -> tuple[int, ...]:
    """A version as comparable integers, ignoring any pre-release suffix."""
    core = version.strip().lstrip("v").split("-")[0]
    parts: list[int] = []
    for chunk in core.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


@lru_cache(maxsize=8)
def binary_version(tf_command: str) -> str:
    """The version the binary reports, or "" if it will not say.

    Cached: a stir run asks once per binary, not once per directory. An
    unanswerable version returns "" and every floor check passes, because
    refusing to run a directory over a version we could not read would turn a
    diagnostic aid into an obstacle.
    """
    try:
        out = subprocess.run(
            [tf_command, "version", "-json"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if out.returncode == 0:
            return str(json.loads(out.stdout).get("terraform_version", ""))
    except (OSError, ValueError, subprocess.SubprocessError):
        return ""
    return ""


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


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
    opentofu_min: str = ""
    terraform_min: str = ""
    init_flags: list[str] = field(factory=list)
    env: list[str] = field(factory=list)
    network: list[str] = field(factory=list)
    reasons: list[str] = field(factory=list)

    def absorb(self, block: dict[str, object]) -> None:
        if block.get("opentofu") is False:
            self.opentofu = False
        for key in ("opentofu_min", "terraform_min"):
            value = block.get(key)
            if isinstance(value, str) and value:
                current = getattr(self, key)
                # Highest floor wins: a directory runs only where every example in
                # it can.
                if not current or _parse(value) > _parse(current):
                    setattr(self, key, value)
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
        opentofu_min=merged.opentofu_min,
        terraform_min=merged.terraform_min,
        init_flags=tuple(merged.init_flags),
        env=tuple(merged.env),
        network=tuple(merged.network),
        reason="; ".join(merged.reasons),
    )


# 🍲📋🔚

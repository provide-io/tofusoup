#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Memray stress test for Terraform state parsing hot paths.

Targets: load_terraform_state, find_resources_with_private_state,
_get_target_resources -- the primary user-facing latency path when
running `soup state show`.
"""

import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("LOG_LEVEL", "ERROR")

from tofusoup.state import (
    find_resources_with_private_state,
    load_terraform_state,
)


def _build_synthetic_state(num_resources: int = 50) -> dict:
    """Build a realistic synthetic Terraform state with many resources."""
    resources = []
    for i in range(num_resources):
        instances = [
            {
                "schema_version": 0,
                "attributes": {
                    "id": f"res-{i}",
                    "name": f"resource-{i}",
                    "tags": {"env": "test", "index": str(i)},
                    "arn": f"arn:aws:ec2:us-east-1:123456789012:instance/i-{i:08x}",
                    "status": "running",
                    "config": {"nested": {"key": f"value-{i}", "list": list(range(10))}},
                },
                "sensitive_attributes": [],
            }
        ]
        # Every 5th resource has private state
        if i % 5 == 0:
            instances[0]["private"] = "eyJzY2hlbWFfdmVyc2lvbiI6IjIifQ=="
        resources.append(
            {
                "mode": "managed",
                "type": f"aws_instance_{i % 10}",
                "name": f"example_{i}",
                "provider": 'provider["registry.terraform.io/hashicorp/aws"]',
                "instances": instances,
            }
        )
    return {
        "version": 4,
        "terraform_version": "1.9.0",
        "serial": 42,
        "lineage": "abc-def-123",
        "outputs": {f"output_{i}": {"value": f"val-{i}", "type": "string"} for i in range(20)},
        "resources": resources,
    }


def main() -> None:
    state_small = _build_synthetic_state(50)
    state_medium = _build_synthetic_state(200)
    state_large = _build_synthetic_state(500)

    # Write state files to temp directory
    tmpdir = Path(tempfile.mkdtemp())
    paths = {}
    for label, state_data in [("small", state_small), ("medium", state_medium), ("large", state_large)]:
        p = tmpdir / f"{label}.tfstate"
        p.write_text(json.dumps(state_data))
        paths[label] = p

    # Warmup
    for _ in range(5):
        s = load_terraform_state(paths["small"])
        find_resources_with_private_state(s)

    # Stress: parse + extract resources across sizes
    cycles = 200
    for i in range(cycles):
        for label in ("small", "medium", "large"):
            state = load_terraform_state(paths[label])
            find_resources_with_private_state(state)

    # Cleanup
    for p in paths.values():
        p.unlink(missing_ok=True)
    tmpdir.rmdir()

    print(f"State parsing stress test complete: {cycles * 3} total parse+extract cycles")


if __name__ == "__main__":
    main()

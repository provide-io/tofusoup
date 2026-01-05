#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TofuSoup conformance test module."""

import json
from pathlib import Path
from typing import Any

from tofusoup.common.exceptions import HarnessError

# THE FIX: Import the existing, correct encoder from the common utils.
from tofusoup.common.utils import DecimalAwareJSONEncoder

from ..cli_verification.shared_cli_utils import run_harness_cli

# The redundant CustomJSONEncoder class has been removed.


def tfwire_go_encode(
    harness_executable_path: Path,
    cty_type_json: Any,
    cty_value_json: Any,
    project_root: Path | None = None,
    test_id: str = "tfwire_encode_test",
) -> bytes:
    """Encodes a value using the go-wire harness."""
    # Encode the type specification as JSON
    type_json_str = json.dumps(cty_type_json, cls=DecimalAwareJSONEncoder)
    # Encode just the value as JSON (not the entire payload)
    value_json_str = json.dumps(cty_value_json, cls=DecimalAwareJSONEncoder)

    if not project_root:
        project_root = Path.cwd()

    exit_code, stdout, stderr = run_harness_cli(
        executable=harness_executable_path,
        args=["wire", "encode", "-", "--type", type_json_str],
        project_root=project_root,
        harness_artifact_name="go-wire-harness",
        test_id=test_id,
        stdin_input=value_json_str,
    )

    if exit_code != 0:
        raise HarnessError("go-wire harness 'encode' failed", stderr=stderr, stdout=stdout)

    return stdout.strip().encode("utf-8")


# 🥣🔬🔚

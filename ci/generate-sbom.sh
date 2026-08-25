#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Write a CycloneDX SBOM describing the wheel this release is publishing.
#
# `cyclonedx-py environment` inspects a Python environment, and with no path it
# inspects the current one. Run under `uvx`, that is the ephemeral environment
# holding cyclonedx-py itself -- so every SBOM published that way listed the SBOM
# tool's own dependencies and not one line of the package being released. That is
# worse than shipping none: a CVE sweep querying it gets a confident wrong answer.
#
# So: install the built wheel into a throwaway environment, and describe that.
# From the wheel rather than from PyPI, because this run's version may not be
# visible there yet and we want the artifact actually being shipped.

set -euo pipefail

DIST_DIR="${1:-dist}"
OUTPUT="${2:-sbom-python.cdx.json}"
ENV_DIR="$(mktemp -d)/sbom-env"

wheel="$(find "$DIST_DIR" -name '*.whl' -print -quit)"
if [ -z "$wheel" ]; then
    echo "::error::no wheel found in ${DIST_DIR}/ to describe"
    exit 1
fi
echo "📦 Describing $(basename "$wheel")"

uv venv --python 3.11 "$ENV_DIR"
VIRTUAL_ENV="$ENV_DIR" uv pip install "$wheel"
uvx --from cyclonedx-bom cyclonedx-py environment "$ENV_DIR/bin/python" \
    --output-format json -o "$OUTPUT"

# A guard against the exact failure above returning quietly: the SBOM has to
# name the package it claims to describe.
python3 - "$wheel" "$OUTPUT" <<'PYEOF'
import json
import pathlib
import sys

wheel, output = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
expected = wheel.name.split("-")[0].replace("_", "-").lower()
names = {c["name"].replace("_", "-").lower() for c in json.loads(output.read_text())["components"]}
if expected not in names:
    print(f"::error::SBOM does not name {expected}; it describes {len(names)} other packages")
    raise SystemExit(1)
print(f"✅ SBOM names {expected} among {len(names)} components")
PYEOF

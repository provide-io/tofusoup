#!/usr/bin/env python3
"""Memray stress test for wire serialization hot paths.

Targets: JSON <-> msgpack conversion in tofusoup.wire.logic --
the data pipeline path used when converting between formats.
"""

import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("LOG_LEVEL", "ERROR")

from tofusoup.wire.logic import convert_json_to_msgpack, convert_msgpack_to_json


def _build_payload(num_entries: int = 100) -> dict:
    """Build a realistic nested payload for serialization stress."""
    return {
        "resources": [
            {
                "type": f"aws_instance_{i}",
                "name": f"node_{i}",
                "attributes": {
                    "id": f"i-{i:012x}",
                    "tags": {"Name": f"node-{i}", "env": "prod"},
                    "metadata": list(range(20)),
                    "config": {"nested": {"deep": {"value": i}}},
                },
            }
            for i in range(num_entries)
        ],
        "outputs": {f"out_{i}": {"value": f"result-{i}"} for i in range(50)},
    }


def main() -> None:
    tmpdir = Path(tempfile.mkdtemp())

    payload_small = _build_payload(50)
    payload_large = _build_payload(300)

    # Write source JSON files
    small_json = tmpdir / "small.json"
    large_json = tmpdir / "large.json"
    small_json.write_text(json.dumps(payload_small))
    large_json.write_text(json.dumps(payload_large))

    # Warmup
    for _ in range(5):
        mp = convert_json_to_msgpack(small_json, tmpdir / "warmup.msgpack")
        convert_msgpack_to_json(mp, tmpdir / "warmup_back.json")

    # Stress: round-trip conversions
    cycles = 300
    for i in range(cycles):
        src = small_json if i % 3 != 0 else large_json
        label = "small" if i % 3 != 0 else "large"
        mp_out = tmpdir / f"{label}_{i}.msgpack"
        json_out = tmpdir / f"{label}_{i}_back.json"

        mp_path = convert_json_to_msgpack(src, mp_out)
        convert_msgpack_to_json(mp_path, json_out)

        # Cleanup intermediate files to avoid filling disk
        mp_out.unlink(missing_ok=True)
        json_out.unlink(missing_ok=True)

    # Final cleanup
    for f in tmpdir.iterdir():
        f.unlink(missing_ok=True)
    tmpdir.rmdir()

    print(f"Wire serialization stress test complete: {cycles} round-trip cycles")


if __name__ == "__main__":
    main()

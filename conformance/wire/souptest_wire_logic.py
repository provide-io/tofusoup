#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import json
from pathlib import Path

import msgpack
import pytest

from tofusoup.wire.logic import convert_json_to_msgpack, convert_msgpack_to_json


@pytest.fixture
def sample_data() -> dict:
    """Provides a simple dictionary for conversion tests."""
    return {"hello": "world", "value": 42}


def test_convert_json_to_msgpack(tmp_path: Path, sample_data: dict) -> None:
    """Verify that a JSON file is correctly converted to MessagePack."""
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(sample_data))

    msgpack_file = convert_json_to_msgpack(json_file, None)

    assert msgpack_file.exists()
    assert msgpack.unpackb(msgpack_file.read_bytes()) == sample_data


def test_convert_msgpack_to_json(tmp_path: Path, sample_data: dict) -> None:
    """Verify that a MessagePack file is correctly converted to JSON."""
    msgpack_file = tmp_path / "test.msgpack"
    msgpack_file.write_bytes(msgpack.packb(sample_data))

    json_file = convert_msgpack_to_json(msgpack_file, None)

    assert json_file.exists()
    assert json.loads(json_file.read_text()) == sample_data


# 🥣🔬🔚

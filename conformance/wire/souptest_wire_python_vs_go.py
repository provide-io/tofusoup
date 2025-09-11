import base64
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
pytest.skip("Wire encoding functions not yet implemented", allow_module_level=True)
# from tofusoup.wire.logic import encode_value_to_tfwire
# Corrected import path
from ..utils.go_interaction import tfwire_go_encode
from tofusoup.common.exceptions import ConversionError, HarnessError

BIT_FOR_BIT_VECTORS = [
    ("simple_string", {"type": "string", "value": "hello"}),
    ("simple_int", {"type": "number", "value": 123}),
    ("simple_float", {"type": "number", "value": 123.45}),
    ("high_precision_decimal", {"type": "number", "value": "9876543210.123456789"}),
    ("bool_true", {"type": "bool", "value": True}),
    ("null_string", {"type": "string", "value": None}),
    ("list_string", {"type": ["list", "string"], "value": ["a", "b", "c"]}),
    ("dynamic_string", {"type": "dynamic", "value": "a dynamic string"}),
    ("dynamic_object", {"type": "dynamic", "value": {"id": "789", "enabled": True}}),
]

@pytest.mark.harness_go
@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
@pytest.mark.parametrize("test_name, payload", BIT_FOR_BIT_VECTORS)
def test_python_and_go_encoders_are_identical(test_name: str, payload: dict, go_harness_executable: Path, project_root: Path):
    try:
        py_b64_msgpack_str = encode_value_to_tfwire(payload)
        py_msgpack_bytes = base64.b64decode(py_b64_msgpack_str)
    except ConversionError as e:
        pytest.fail(f"Python wire encoding failed for '{test_name}': {e}")

    try:
        go_b64_msgpack_bytes = tfwire_go_encode(
            harness_executable_path=go_harness_executable,
            cty_type_json=payload["type"],
            cty_value_json=payload["value"],
            project_root=project_root,
            test_id=f"wire_encode_{test_name}"
        )
        go_msgpack_bytes = base64.b64decode(go_b64_msgpack_bytes)
    except Exception as e:
        pytest.fail(f"Go harness 'tfwire_go_encode' failed for test '{test_name}': {e}")

    assert py_msgpack_bytes == go_msgpack_bytes, (
        f"Binary mismatch for test '{test_name}'\n"
        f"Python produced b64: {py_b64_msgpack_str}\n"
        f"Go produced b64:     {go_b64_msgpack_bytes.decode()}"
    )

# 🍲🥄🧪🪄

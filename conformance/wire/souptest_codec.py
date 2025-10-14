from decimal import Decimal

import pytest

from pyvider.cty.conversion import cty_to_native
from pyvider.cty.types import CtyNumber, CtyObject, CtyString
from pyvider.cty.values import CtyValue


@pytest.mark.integration_cty
@pytest.mark.xfail(
    reason="pyvider-cty validation hits 30s timeout due to recursion detection issues. "
    "See: https://github.com/provide-io/pyvider-cty/issues/TBD"
)
def test_decode_simple_attributes():
    """Verify decoding of a simple flat object."""
    schema = CtyObject({"name": CtyString(), "age": CtyNumber()})
    data = {"name": "Alice", "age": 30}

    decoded_value = schema.validate(data)

    assert isinstance(decoded_value, CtyValue)
    assert not decoded_value.is_null
    assert not decoded_value.vtype.is_primitive_type()
    assert decoded_value.value["name"].value == "Alice"
    assert decoded_value.value["age"].value == Decimal("30")


@pytest.mark.integration_cty
def test_roundtrip_simple_data():
    """Verify that encoding then decoding a value yields the original."""
    schema = CtyObject({"name": CtyString(), "age": CtyNumber()})
    original_value = schema.validate({"name": "Bob", "age": 42})

    encoded_data = cty_to_native(original_value)
    decoded_value = schema.validate(encoded_data)

    assert decoded_value == original_value


# 🍲🥄🧪🪄

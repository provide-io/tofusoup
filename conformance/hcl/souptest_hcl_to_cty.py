from decimal import Decimal
from pathlib import Path

import pytest

# Corrected import from the canonical pyvider library
from pyvider.cty.types import CtyNumber, CtyObject, CtyString
from tofusoup.hcl.logic import load_hcl_file_as_cty


@pytest.mark.integration_hcl
def test_souptest_load_hcl_file_as_cty_simple(tmp_path: Path):
    """
    Verify that a simple HCL file is parsed into a correct CtyValue.
    This is a conformance test.
    """
    hcl_content = """
    name = "test-server-conformance"
    instance_count = 5
    """
    hcl_file = tmp_path / "test.hcl"
    hcl_file.write_text(hcl_content)

    cty_value = load_hcl_file_as_cty(str(hcl_file))

    assert isinstance(cty_value.vtype, CtyObject)
    assert "name" in cty_value.value
    assert "instance_count" in cty_value.value

    assert cty_value.value["name"].vtype == CtyString()
    assert cty_value.value["name"].value == "test-server-conformance"

    assert cty_value.value["instance_count"].vtype == CtyNumber()
    assert cty_value.value["instance_count"].value == Decimal("5")


# 🍲🥄🧪🪄

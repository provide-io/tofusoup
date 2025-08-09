from pathlib import Path
from decimal import Decimal
import pytest

from tofusoup.hcl.logic import load_hcl_file_as_cty
from pyvider.cty.types import CtyObject, CtyString, CtyNumber

def test_load_hcl_file_as_cty_simple(tmp_path: Path):
    """Verify that a simple HCL file is parsed into a correct CtyValue."""
    hcl_content = """
    name = "test-server"
    instance_count = 3
    """
    hcl_file = tmp_path / "test.hcl"
    hcl_file.write_text(hcl_content)
    
    cty_value = load_hcl_file_as_cty(str(hcl_file))
    
    assert isinstance(cty_value.vtype, CtyObject)
    assert "name" in cty_value.value
    assert "instance_count" in cty_value.value
    
    assert cty_value.value["name"].vtype == CtyString()
    assert cty_value.value["name"].value == "test-server"
    
    assert cty_value.value["instance_count"].vtype == CtyNumber()
    assert cty_value.value["instance_count"].value == Decimal("3")

# 🍲🥄🧪🪄

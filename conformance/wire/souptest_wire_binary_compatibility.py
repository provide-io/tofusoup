import pytest
from pathlib import Path

# This test is a placeholder for future binary compatibility tests.
# It now correctly requests the generic harness fixture.
@pytest.mark.skip(reason="Binary compatibility test suite not yet fully implemented.")
@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
def test_harness_can_encode_simple_object(go_harness_executable: Path):
    assert go_harness_executable.exists()

# 🍲🥄🧪🪄

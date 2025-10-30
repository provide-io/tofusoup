#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from pathlib import Path

import pytest


# This test is a placeholder for future binary compatibility tests.
# It now correctly requests the generic harness fixture.
@pytest.mark.harness_go
@pytest.mark.skip(reason="Binary compatibility test suite not yet fully implemented.")
@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
def test_harness_can_encode_simple_object(go_harness_executable: Path) -> None:
    assert go_harness_executable.exists()


# 🥣🔬🔚

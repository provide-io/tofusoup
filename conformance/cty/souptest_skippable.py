#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import os

import pytest


@pytest.mark.integration_cty
def test_always_passes() -> None:
    assert True


@pytest.mark.skip(reason="This test is intentionally skipped.")
def test_always_skip_me() -> None:
    raise AssertionError()


@pytest.mark.integration_cty
def test_check_env_vars_cty_suite() -> None:
    """Checks if environment variables from soup.toml are set for the cty suite."""
    assert os.getenv("TOFUSOUP_TEST_DEFAULT_ENV") == "cty_override_default_env_from_toml"
    assert os.getenv("TOFUSOUP_CTY_SUITE_ENV") == "cty_specific_env_value_from_toml"


# 🥣🔬🔚

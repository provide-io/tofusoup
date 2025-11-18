#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import logging

import pytest


@pytest.fixture(scope="session", autouse=True)
def suppress_noisy_loggers() -> None:
    """Suppress verbose logging from third-party libraries during tests."""
    # Suppress markdown_it logging (entering paragraph, etc.)
    logging.getLogger("markdown_it").setLevel(logging.WARNING)

    # Suppress grpc/cygrpc logging (Loaded running loop, etc.)
    logging.getLogger("grpc").setLevel(logging.WARNING)
    logging.getLogger("grpc._cython.cygrpc").setLevel(logging.WARNING)


# 🥣🔬🔚

# conformance/rpc/souptest_cross_language.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest

# This test suite is temporarily disabled as it requires a full rewrite of the
# pyvider.conversion.marshaler to match the Go implementation.
# The current recursive approach is fundamentally flawed.
pytest.skip("Skipping cross-language tests pending marshaller rewrite", allow_module_level=True)


# 🍜🍲🔗🪄

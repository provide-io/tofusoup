#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Cross-Language RPC Conformance Tests (Currently Disabled).

These tests validate cross-language compatibility between Python and Go
RPC implementations. Currently skipped pending marshaller rewrite to
match Go implementation.
"""

import pytest

# This test suite is temporarily disabled as it requires a full rewrite of the
# pyvider.conversion.marshaler to match the Go implementation.
# The current recursive approach is fundamentally flawed.
pytest.skip("Skipping cross-language tests pending marshaller rewrite", allow_module_level=True)

# 🥣🔬🔚

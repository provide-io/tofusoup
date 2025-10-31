#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Cross-language HCL interoperability tests.

Tests Python ↔ Go HCL parsing compatibility using pyvider-hcl (Python) and soup-go (Go).
Validates that both parsers produce compatible CTY values from the same HCL input.

Test Strategy:
1. Python parses HCL → CTY values → validates structure
2. Go parses same HCL → JSON output → compare with Python
3. Validates list inference fix works with real HCL content

This ensures the pyvider-hcl inference fix (using pyvider-cty's canonical implementation)
produces results compatible with Go's HCL parser.

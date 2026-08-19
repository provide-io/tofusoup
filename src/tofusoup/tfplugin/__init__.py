#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Drive a packaged Terraform provider over tfplugin6.

`tofusoup.rpc` covers the go-plugin *transport* -- handshake, mTLS, cross
language. This covers the layer above it: speaking the Terraform plugin
protocol to a provider binary the way Terraform itself would, so a provider can
be conformance-tested as the artifact it ships rather than as the handlers it
was built from.
"""

from tofusoup.tfplugin.driver import (
    MAGIC_COOKIE_KEY,
    MAGIC_COOKIE_VALUE,
    TfPluginProvider,
    base_env,
    diagnostic_text,
    errors,
    pack,
    start_provider,
    unpack,
)

__all__ = [
    "MAGIC_COOKIE_KEY",
    "MAGIC_COOKIE_VALUE",
    "TfPluginProvider",
    "base_env",
    "diagnostic_text",
    "errors",
    "pack",
    "start_provider",
    "unpack",
]

# 🥣🔬🔚

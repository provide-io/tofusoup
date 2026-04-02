#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import asyncio
import sys

# Windows requires ProactorEventLoop for subprocess support (create_subprocess_exec).
# Must be set before any event loop is created.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from provide.foundation.utils.versioning import get_version

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

__version__ = get_version("tofusoup", __file__)

__all__ = [
    "__version__",
]

# 🥣🔬🔚

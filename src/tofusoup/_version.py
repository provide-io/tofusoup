from __future__ import annotations

from provide.foundation.utils.versioning import get_version

"""Version handling for tofusoup.

This module uses the shared versioning utility from provide-foundation.
"""

__version__ = get_version("tofusoup", caller_file=__file__)

__all__ = ["__version__"]

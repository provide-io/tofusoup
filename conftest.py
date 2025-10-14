# This is the root conftest.py for the TofuSoup project.

# pytest_plugins should be defined in a top-level conftest file.
# This is where plugins that need to be available for the entire test suite
# should be registered. For example, if a plugin like 'pytester' was
# being used in a sub-directory's conftest, it would be moved here.
#
# Example:
# pytest_plugins = ["pytester"]

# For now, this file establishes the correct location for such definitions.
# Add any required top-level plugins here.

# Import pytest hooks to suppress noisy loggers during tests
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


# 🍲🥄🧪🪄

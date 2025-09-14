#
# tofusoup/wire/logging.py
#
"""Centralized logging configuration using Pyvider Telemetry."""

from provide.foundation import LoggingConfig, TelemetryConfig, get_hub
from tofusoup.config.defaults import DEFAULT_LOG_LEVEL


def configure_logging() -> None:
    """
    Configures Pyvider Telemetry for the library.

    This setup ensures that all log output is structured as JSON and directed
    to STDERR, preventing interference with the wire protocol's STDOUT/STDIN.
    """
    config = TelemetryConfig(
        logging=LoggingConfig(
            console_formatter="json",
            default_level=DEFAULT_LOG_LEVEL,
            das_emoji_prefix_enabled=True,
            logger_name_emoji_prefix_enabled=False,
        )
    )
    hub = get_hub()
    hub.initialize_foundation(config=config)


# <3 🍲 🍜 🍥>


# 🍲🥄📄🪄

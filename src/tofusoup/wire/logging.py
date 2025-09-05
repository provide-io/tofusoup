#
# tofusoup/wire/logging.py
#
"""Centralized logging configuration using Pyvider Telemetry."""

from provide.foundation import LoggingConfig, TelemetryConfig, setup_telemetry


def configure_logging():
    """
    Configures Pyvider Telemetry for the library.

    This setup ensures that all log output is structured as JSON and directed
    to STDERR, preventing interference with the wire protocol's STDOUT/STDIN.
    """
    config = TelemetryConfig(
        logging=LoggingConfig(
            console_formatter="json",
            default_level="INFO",
            das_emoji_prefix_enabled=True,
            logger_name_emoji_prefix_enabled=False,
        )
    )
    setup_telemetry(config)


# <3 🍲 🍜 🍥>


# 🍲🥄📄🪄

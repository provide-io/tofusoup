#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Centralized logging configuration using Pyvider Telemetry."""

from attrs import evolve
from provide.foundation import TelemetryConfig, get_hub

from tofusoup.common.config import TofuSoupConfig


def configure_logging() -> None:
    """
    Configures Pyvider Telemetry for the library.

    This setup ensures that all log output is structured as JSON and directed
    to STDERR, preventing interference with the wire protocol's STDOUT/STDIN.
    """
    # Load TofuSoup configuration from environment
    tofusoup_config = TofuSoupConfig.from_env()

    # Get base telemetry config from environment
    base_telemetry = TelemetryConfig.from_env()

    # Merge with wire-specific settings
    config = evolve(
        base_telemetry,
        service_name="tofusoup-wire",
        logging=evolve(
            base_telemetry.logging,
            console_formatter="json",
            default_level=tofusoup_config.log_level,  # type: ignore[arg-type]
            das_emoji_prefix_enabled=True,
            logger_name_emoji_prefix_enabled=False,
        ),
    )

    hub = get_hub()
    hub.initialize_foundation(config=config)


# 🥣🔬🔚

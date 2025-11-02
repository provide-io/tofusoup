#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import os
from pathlib import Path
import shutil

from tofusoup.common.utils import get_cache_dir
from tofusoup.config.defaults import (
    ENV_PYVIDER_PRIVATE_STATE_SHARED_SECRET,
    ENV_TF_DATA_DIR,
    ENV_TF_LOG,
)

# Configuration constants
TF_COMMAND = shutil.which("tofu") or shutil.which("terraform") or "tofu"
MAX_CONCURRENT_TESTS = os.cpu_count() or 4
LOGS_DIR = get_cache_dir() / "logs" / "stir"

# Runtime configuration
DEFAULT_PLUGIN_CACHE_DIR = Path.home() / ".terraform.d" / "plugin-cache"
STIR_PLUGIN_CACHE_DIR = Path.home() / ".tofusoup" / "plugin-cache"
PROVIDER_PREPARATION_TIMEOUT = 300  # 5 minutes

# Environment variable names
ENV_VARS = {
    "TF_LOG": ENV_TF_LOG,
    "TF_DATA_DIR": ENV_TF_DATA_DIR,
    "PYVIDER_PRIVATE_STATE_SHARED_SECRET": ENV_PYVIDER_PRIVATE_STATE_SHARED_SECRET,
}

# Phase emojis for status display
# These appear in the "Phase" column (column 2) of the status table
PHASE_EMOJI = {
    "PENDING": "💤",  # Test queued, not started yet
    "SCANNING": "🔍",  # Scanning for provider requirements
    "DOWNLOADING": "📥",  # Downloading providers to cache
    "CLEANING": "🧹",  # Removing old .terraform directories
    "INIT": "🔄",  # Running terraform init
    "APPLYING": "🚀",  # Running terraform apply
    "DESTROYING": "💥",  # Running terraform destroy
    "FAIL": "❌",  # Test failed (terraform command returned non-zero)
    "ERROR": "🔥",  # Critical error/exception in test harness
    "SKIPPED": "⏭️",  # Test skipped (no .tf files or other reason)
}

# 🥣🔬🔚

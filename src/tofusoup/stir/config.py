#
# tofusoup/stir/config.py
#

import os
from pathlib import Path
import shutil

from tofusoup.config.defaults import (
    ENV_PYVIDER_PRIVATE_STATE_SHARED_SECRET,
    ENV_TF_DATA_DIR,
    ENV_TF_LOG,
)

# Configuration constants
TF_COMMAND = shutil.which("tofu") or shutil.which("terraform") or "tofu"
MAX_CONCURRENT_TESTS = os.cpu_count() or 4
LOGS_DIR = Path("output/")

# Environment variable names
ENV_VARS = {
    "TF_LOG": ENV_TF_LOG,
    "TF_DATA_DIR": ENV_TF_DATA_DIR,
    "PYVIDER_PRIVATE_STATE_SHARED_SECRET": ENV_PYVIDER_PRIVATE_STATE_SHARED_SECRET,
}

# Phase emojis for status display
PHASE_EMOJI = {
    "PENDING": "⏳",
    "CLEANING": "🧹",
    "INIT": "🔄",
    "APPLYING": "🚀",
    "ANALYZING": "🔬",
    "DESTROYING": "💥",
    "PASS": "✅",
    "FAIL": "❌",
    "ERROR": "🔥",
    "SKIPPED": "⏭️",
}

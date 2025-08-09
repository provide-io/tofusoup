# src/tofusoup/conformance/utils/__init__.py
"""
TofuSoup Conformance Test Utilities Package.
"""
# THE FIX: Only export functions that actually exist in go_interaction.py
from .go_interaction import HarnessError, tfwire_go_encode

__all__ = [
    "HarnessError",
    "tfwire_go_encode",
]

# 🍲🥄📄🪄

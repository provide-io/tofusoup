#
# tofusoup/common/exceptions.py
#
"""
Common exceptions for the TofuSoup application.
"""

from provide.foundation.errors import FoundationError


class TofuSoupError(FoundationError):
    """Base class for exceptions in TofuSoup."""

    pass


class ConversionError(TofuSoupError):
    """Custom exception for errors during data conversion (e.g., HCL to JSON, CTY operations)."""

    pass


class TofuSoupConfigError(TofuSoupError):
    """Custom exception for errors related to TofuSoup configuration loading or validation."""

    pass


# Add other general TofuSoup errors here as needed.
# For specific errors like HarnessBuildError, they are defined in their respective modules (e.g., harness/logic.py)
# but could also inherit from TofuSoupError if desired for a common hierarchy.


class HarnessError(TofuSoupError):
    """Custom exception for errors interacting with external test harness."""

    def __init__(
        self,
        message: str,
        stderr: str | bytes | None = None,
        stdout: str | bytes | None = None,
        details: str | None = None,
    ):
        full_message = message
        if details:
            full_message += f"\nDetails: {details}"
        if stdout:
            stdout_str = (
                stdout.decode("utf-8", "replace")
                if isinstance(stdout, bytes)
                else stdout
            )
            full_message += f"\n--- HARNESS STDOUT ---\n{stdout_str.strip()}"
        if stderr:
            stderr_str = (
                stderr.decode("utf-8", "replace")
                if isinstance(stderr, bytes)
                else stderr
            )
            full_message += f"\n--- HARNESS STDERR ---\n{stderr_str.strip()}"

        super().__init__(full_message)
        self.stdout = (
            stdout.decode("utf-8", "replace").strip()
            if isinstance(stdout, bytes)
            else stdout.strip()
            if stdout
            else None
        )
        self.stderr = (
            stderr.decode("utf-8", "replace").strip()
            if isinstance(stderr, bytes)
            else stderr.strip()
            if stderr
            else None
        )
        self.details = details


# <3 🍲 🍜 🍥>


# 🍲🥄⚠️🪄

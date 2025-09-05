#
# tofusoup/common/exceptions.py
#
"""
Common exceptions for the TofuSoup application.
"""

from provide.foundation.errors import FoundationError, ProcessError


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


class HarnessError(ProcessError):
    """Custom exception for errors interacting with external test harness."""

    def __init__(
        self,
        message: str,
        *,
        stderr: str | bytes | None = None,
        stdout: str | bytes | None = None,
        details: str | None = None,
        command: str | list[str] | None = None,
        return_code: int | None = None,
    ):
        # Store details separately for backward compatibility
        self.details = details
        
        # Pass to ProcessError which handles stdout/stderr formatting
        super().__init__(
            message,
            command=command,
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
            harness_details=details  # Store in context
        )


# <3 🍲 🍜 🍥>


# 🍲🥄⚠️🪄

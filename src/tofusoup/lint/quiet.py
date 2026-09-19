# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Scoped suppression for third-party provider client chatter."""

from collections.abc import Iterator
from contextlib import contextmanager
import os
from pathlib import Path
import sys


@contextmanager
def silence_stderr() -> Iterator[None]:
    """Hide transient provider-launch logs while a public lint lane runs.

    The RPC client and provider launcher both use stderr for verbose lifecycle
    messages. Lint findings are returned over RPC and rendered on stdout after
    this context exits, while launch and RPC exceptions are still converted to
    ordinary CLI errors by the caller.
    """
    sys.stderr.flush()
    saved_stderr = os.dup(2)
    try:
        with Path(os.devnull).open("w", encoding="utf-8") as sink:
            os.dup2(sink.fileno(), 2)
            yield
    finally:
        sys.stderr.flush()
        os.dup2(saved_stderr, 2)
        os.close(saved_stderr)

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import threading
from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog


class LogViewer(Widget):
    """A widget to display application logs."""

    DEFAULT_CSS = """
    LogViewer {
        height: 10;
        border-top: thick $surface-darken-1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._log_widget = RichLog(wrap=True, highlight=True, markup=True)
        self.border_title = "🪵 Logs"

    def compose(self) -> ComposeResult:
        yield self._log_widget

    def write(self, text: str) -> None:
        """
        Write a line of text to the log. This method is thread-safe.
        """
        # FIX: Check if we are on the app's thread. If so, write directly.
        # Otherwise, use call_from_thread. This is the definitive fix.
        if self.app.is_running and self.app._thread_id == threading.get_ident():
            self._log_widget.write(Text.from_ansi(text.strip()))
        else:
            self.app.call_from_thread(self._log_widget.write, Text.from_ansi(text.strip()))

    def flush(self) -> None:
        """A no-op flush method to satisfy the stream protocol."""

    def clear(self) -> None:
        """Clear the log."""
        self._log_widget.clear()


# 🥣🔬🔚

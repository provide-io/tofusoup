#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from typing import Any

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Markdown

from tofusoup.registry.search.engine import SearchResult


class DetailView(VerticalScroll):
    """A widget to display details of a selected search result."""

    DEFAULT_CSS = """
    DetailView {
        padding: 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._markdown = Markdown()
        self._raw_markdown_content = ""

    @property
    def raw_content(self) -> str:
        """Exposes the raw markdown string for reliable testing."""
        return self._raw_markdown_content

    def on_mount(self) -> None:
        """Set the initial content when the widget is mounted."""
        initial_content = "No item selected."
        self._raw_markdown_content = initial_content
        self._markdown.update(initial_content)

    def compose(self) -> ComposeResult:
        yield self._markdown

    def update_content(self, result: SearchResult | None) -> None:
        """Update the content of the detail view. This is a synchronous method."""
        if result:
            name = f"{result.namespace}/{result.name}"
            if result.type == "module":
                name += f"/{result.provider_name}"

            markdown_doc = f"""
# {name}

- **Type**: {result.type}
- **Registry**: {result.registry_source}
- **Latest Version**: {result.latest_version or "N/A"}
- **Total Versions**: {result.total_versions or "N/A"}

---

{result.description or "No description available."}
"""
            self._raw_markdown_content = markdown_doc
            self._markdown.update(markdown_doc)
        else:
            no_item_content = "No item selected."
            self._raw_markdown_content = no_item_content
            self._markdown.update(no_item_content)


# 🥣🔬🔚

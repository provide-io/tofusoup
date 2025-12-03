#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import DataTable, Input, LoadingIndicator, Static
from textual.widgets._data_table import RowDoesNotExist
from textual.widgets.data_table import RowKey

from tofusoup.registry.search.engine import SearchResult

if TYPE_CHECKING:
    pass


class SearchView(Vertical):
    """A widget combining a search input and a results data table."""

    DEFAULT_CSS = """
    SearchView {
        layout: vertical;
        overflow: hidden;
    }
    #search_input {
        dock: top;
        margin-bottom: 1;
    }
    #results_table {
        height: 1fr;
    }
    #loading_indicator {
        display: none;
        height: auto;
        margin: 1 2;
    }
    """

    class SearchSubmitted(Message):
        def __init__(self, query: str) -> None:
            super().__init__()
            self.query: str = query

    class ResultSelected(Message):
        def __init__(self, result: SearchResult) -> None:
            super().__init__()
            self.result: SearchResult = result

    SORT_KEYS: ClassVar[list[str]] = ["versions", "name"]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._results_map: dict[RowKey, SearchResult] = {}

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search modules and providers...", id="search_input")
        yield LoadingIndicator(id="loading_indicator")
        yield DataTable(id="results_table")

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_column("R", key="registry", width=3)
        table.add_column("T", key="type", width=3)
        table.add_column("Name", key="name", width=40)
        table.add_column("Versions", key="versions", width=10)
        table.add_column("Latest", key="latest", width=15)
        table.add_column("Description", key="description", width=None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search_input":
            self.post_message(self.SearchSubmitted(event.value))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "results_table" and (result := self._results_map.get(event.row_key)):
            self.post_message(self.ResultSelected(result))

    def add_result(self, result: SearchResult) -> None:
        """Adds a single result to the table or updates an existing one."""
        table = self.query_one(DataTable)
        row_key = RowKey(result.id)

        registry_emoji = (
            "🤝"
            if result.registry_source == "both"
            else "🍲"
            if result.registry_source == "opentofu"
            else "🏢"
        )
        type_emoji = "📦" if result.type == "module" else "🔌"
        name = f"{result.namespace}/{result.name}"
        if result.type == "module":
            name += f"/{result.provider_name}"

        total_versions = result.total_versions if result.total_versions is not None else -1

        # FIX: Use the correct `try...except RowDoesNotExist` pattern to check for row existence.
        try:
            table.get_row(row_key)
            # If we get here, the row exists. Update it.
            self._results_map[row_key].registry_source = "both"
            table.update_cell(row_key, "registry", Static("🤝"))
        except RowDoesNotExist:
            # The row does not exist. Add it.
            self._results_map[row_key] = result
            table.add_row(
                Static(registry_emoji),
                Static(type_emoji),
                name,
                total_versions,
                result.latest_version or "N/A",
                result.description or "",
                key=row_key,
            )

        # Re-sort the table after every update
        table.sort(*self.SORT_KEYS, reverse=True)

    def clear_table(self) -> None:
        """Clears all results from the table."""
        self.query_one(DataTable).clear()
        self._results_map.clear()

    def show_loading(self, show: bool) -> None:
        self.query_one(LoadingIndicator).display = show
        self.query_one(DataTable).display = not show


# 🥣🔬🔚

#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from collections.abc import Awaitable, Callable

import pytest
from textual.app import ComposeResult
from textual.message import Message
from textual.pilot import Pilot
from textual.screen import Screen
from textual.widgets import DataTable

from tofusoup.browser.ui.widgets.search_view import SearchView
from tofusoup.registry.search.engine import SearchResult

# Mark all tests in this module as browser tests
pytestmark = pytest.mark.browser


class SearchViewScreen(Screen):
    """A simple screen to host the SearchView widget for testing."""

    def compose(self) -> ComposeResult:
        yield SearchView()


@pytest.fixture
def search_results() -> list[SearchResult]:
    return [
        SearchResult(
            id="1",
            name="Module One",
            type="module",
            namespace="ns",
            provider_name="aws",
            registry_source="tf",
            total_versions=5,
            latest_version="1.0.0",
        ),
        SearchResult(
            id="2",
            name="Module Two",
            type="module",
            namespace="ns",
            provider_name="gcp",
            registry_source="tofu",
            total_versions=10,
            latest_version="2.0.0",
        ),
    ]


async def test_search_view_update_and_display_results(
    pilot: Pilot, search_results: list[SearchResult]
) -> None:
    """Verify search results are correctly displayed in the view."""
    await pilot.app.push_screen(SearchViewScreen())
    await pilot.pause()
    search_view = pilot.app.screen.query_one(SearchView)

    for result in search_results:
        search_view.add_result(result)
    await pilot.pause()

    table = pilot.app.screen.query_one(DataTable)
    assert table.row_count == 2

    name_column_content = [str(cell) for cell in table.get_column("name")]
    assert "ns/Module One/aws" in name_column_content
    assert "ns/Module Two/gcp" in name_column_content


async def test_search_view_result_selection(
    pilot_with_message_capture: Callable[[list[Message]], Awaitable[Pilot]], search_results: list[SearchResult]
) -> None:
    """Verify that selecting a result emits the correct message."""
    messages: list[Message] = []
    async with await pilot_with_message_capture(messages) as pilot:
        await pilot.app.push_screen(SearchViewScreen())
        await pilot.pause()
        search_view = pilot.app.screen.query_one(SearchView)
        for result in search_results:
            search_view.add_result(result)
        await pilot.pause()

        table = pilot.app.screen.query_one(DataTable)
        table.focus()
        # FIX: Remove the erroneous "down" press. The test should select the
        # first item in the sorted list (which is ID "2").
        await pilot.press("enter")
        await pilot.pause()

    result_selected_messages = [msg for msg in messages if isinstance(msg, SearchView.ResultSelected)]
    assert len(result_selected_messages) == 1
    assert result_selected_messages[0].result.id == "2"


async def test_search_view_clear_results(pilot: Pilot, search_results: list[SearchResult]) -> None:
    """Verify the clear_results method empties the list."""
    await pilot.app.push_screen(SearchViewScreen())
    await pilot.pause()
    search_view = pilot.app.screen.query_one(SearchView)
    for result in search_results:
        search_view.add_result(result)
    await pilot.pause()

    table = pilot.app.screen.query_one(DataTable)
    assert table.row_count == 2

    search_view.clear_table()
    await pilot.pause()
    assert table.row_count == 0


# 🥣🔬🔚

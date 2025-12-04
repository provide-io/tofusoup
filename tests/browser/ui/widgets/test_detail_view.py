#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import pytest
from textual.app import ComposeResult
from textual.pilot import Pilot
from textual.screen import Screen

from tofusoup.browser.ui.widgets.detail_view import DetailView
from tofusoup.registry.search.engine import SearchResult

# Mark all tests in this module as browser tests
pytestmark = pytest.mark.browser


class DetailViewScreen(Screen):
    """A simple screen to host the DetailView widget for testing."""

    def compose(self) -> ComposeResult:
        yield DetailView()


async def test_detail_view_initial_state(pilot: Pilot) -> None:
    """Verify the detail view is initially empty."""
    await pilot.app.push_screen(DetailViewScreen())
    await pilot.pause()

    view = pilot.app.screen.query_one(DetailView)
    assert "No item selected" in view.raw_content


async def test_detail_view_update_content(pilot: Pilot) -> None:
    """Verify the detail view can be updated with new content."""
    await pilot.app.push_screen(DetailViewScreen())
    await pilot.pause()
    detail_view = pilot.app.screen.query_one(DetailView)

    result = SearchResult(
        id="1",
        name="test-module",
        namespace="test",
        type="module",
        registry_source="opentofu",
        provider_name="aws",
    )
    detail_view.update_content(result)
    await pilot.pause()

    assert "test/test-module/aws" in detail_view.raw_content
    assert "Type**: module" in detail_view.raw_content


# 🥣🔬🔚

#
# tofusoup/browser/ui/app.py
#

from textual.app import App, ComposeResult
from textual.message import Message
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header

from provide.foundation import LoggingConfig, TelemetryConfig, logger, setup_telemetry
from provide.foundation.core import _set_log_stream_for_testing
from tofusoup.browser.ui.widgets.detail_view import DetailView
from tofusoup.browser.ui.widgets.log_viewer import LogViewer
from tofusoup.browser.ui.widgets.search_view import SearchView
from tofusoup.registry import IBMTerraformRegistry, OpenTofuRegistry, RegistryConfig
from tofusoup.registry.search.engine import SearchEngine, SearchQuery, SearchResult


class MainSearchScreen(Screen[None]):
    """The main screen for search functionality."""

    class NewSearchResult(Message):
        """A message to deliver a single search result as it arrives."""

        def __init__(self, result: SearchResult) -> None:
            super().__init__()
            self.result = result

    class SearchComplete(Message):
        """A message to signal that the search stream has finished."""

        pass

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        yield SearchView()
        yield LogViewer()
        yield Footer()

    def on_mount(self) -> None:
        log_viewer = self.query_one(LogViewer)
        _set_log_stream_for_testing(log_viewer)

        telemetry_config = TelemetryConfig(
            service_name="tofusoup-tui", logging=LoggingConfig(default_level="DEBUG")
        )
        setup_telemetry(telemetry_config)
        logger.info("TUI Logger Initialized. Ready for search.")

    def on_search_view_search_submitted(
        self, event: SearchView.SearchSubmitted
    ) -> None:
        logger.info(f"Search submitted for query: '{event.query}'")
        search_view = self.query_one(SearchView)
        search_view.clear_table()
        search_view.show_loading(True)
        self.run_worker(self.perform_search(event.query), exclusive=True)

    async def perform_search(self, query_term: str) -> None:
        """The background worker that streams results."""
        try:
            registries = [
                IBMTerraformRegistry(
                    config=RegistryConfig(base_url="https://registry.terraform.io")
                ),
                OpenTofuRegistry(),
            ]
            engine = SearchEngine(registries=registries)
            query = SearchQuery(term=query_term)

            async for result in engine.search(query):
                self.post_message(self.NewSearchResult(result))

            await engine.close()
        except Exception as e:
            self.call_from_thread(
                logger.error, f"Error during background search: {e}", exc_info=True
            )
        finally:
            self.post_message(self.SearchComplete())

    def on_main_search_screen_new_search_result(self, message: NewSearchResult) -> None:
        """Handles receiving a single search result from the worker."""
        search_view = self.query_one(SearchView)
        search_view.add_result(message.result)

    def on_main_search_screen_search_complete(self, message: SearchComplete) -> None:
        """Handles the end of the search stream."""
        search_view = self.query_one(SearchView)
        search_view.show_loading(False)
        logger.info("Search stream complete. Results displayed.")
        # FIX: Move focus to the results table for immediate navigation.
        self.query_one(DataTable).focus()

    async def on_search_view_result_selected(
        self, event: SearchView.ResultSelected
    ) -> None:
        logger.info(f"Result selected: {event.result.id}")
        self.app.push_screen(DetailScreen(item_details=event.result))


class DetailScreen(Screen):
    """A screen to display detailed information about an item."""

    # FIX: Add key binding to allow 'escape' to pop the screen.
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(self, item_details: SearchResult, **kwargs) -> None:
        super().__init__(**kwargs)
        self.item_details = item_details

    def compose(self) -> ComposeResult:
        yield Header()
        yield DetailView()
        yield Footer()

    def on_mount(self) -> None:
        detail_view_widget = self.query_one(DetailView)
        detail_view_widget.update_content(self.item_details)


class TFBrowserApp(App[None]):
    """The main tfbrowser TUI application."""

    CSS_PATH = "app.tcss"
    TITLE = "tfbrowser - Terraform/OpenTofu Registry Browser"

    def on_mount(self) -> None:
        self.push_screen(MainSearchScreen())


# 🍲🥄📄🪄

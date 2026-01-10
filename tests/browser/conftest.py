#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from collections.abc import Awaitable, Callable

import pytest_asyncio
from textual.message import Message
from textual.pilot import Pilot

from tofusoup.browser.ui.app import TFBrowserApp


@pytest_asyncio.fixture
async def pilot() -> Pilot:
    """
    Provides a Textual Pilot for interacting with the app.
    This is a simplified version for tests that don't need to capture messages.
    """
    app = TFBrowserApp()
    async with app.run_test() as pilot:
        yield pilot


@pytest_asyncio.fixture
async def pilot_with_message_capture() -> Callable[[list[Message]], Awaitable[Pilot]]:
    """
    Provides a Textual Pilot factory that captures all app messages.
    This is the robust way to test for message emissions.
    """

    async def _pilot_factory(messages: list[Message]) -> Pilot:
        def message_hook(message: Message) -> None:
            messages.append(message)

        app = TFBrowserApp()
        # The context manager will be entered by the test function
        return app.run_test(message_hook=message_hook)

    return _pilot_factory


# 🥣🔬🔚

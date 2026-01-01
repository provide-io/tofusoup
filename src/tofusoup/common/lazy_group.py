#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import importlib
from typing import Any

import click


class LazyGroup(click.Group):
    """
    A Click Group that loads its commands lazily from an import string.
    This prevents importing all command dependencies at application startup,
    which is crucial for performance and avoiding unwanted side effects.
    """

    def __init__(
        self,
        *args: Any,
        lazy_commands: dict[str, tuple[str, str]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.lazy_commands = lazy_commands or {}

    def list_commands(self, ctx: click.Context) -> list[str]:
        """Lists all commands, including eager and lazy ones."""
        base_commands = super().list_commands(ctx)
        # Combine and remove duplicates, then sort.
        return sorted(list(set(base_commands + list(self.lazy_commands.keys()))))

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """
        Gets a command by name. If it's a lazy command, it's imported on-demand.
        """
        if cmd_name in self.lazy_commands:
            try:
                module_path, command_name = self.lazy_commands[cmd_name]
                module = importlib.import_module(module_path)
                cmd: click.Command | None = getattr(module, command_name)
                return cmd
            except (ImportError, AttributeError) as e:
                raise click.UsageError(f"Error loading command '{cmd_name}': {e}") from e
        return super().get_command(ctx, cmd_name)


# 🥣🔬🔚

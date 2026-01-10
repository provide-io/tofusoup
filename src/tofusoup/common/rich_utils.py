#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Utilities for enhancing CLI output using the Rich library."""

import json
from typing import Any

from rich import print as rich_print
from rich.tree import Tree


def build_rich_tree_from_cty_json_comparable(  # noqa: C901
    tree_node: Tree, data: dict[str, Any], name: str = "value"
) -> None:
    """
    Recursively builds a Rich Tree from a CTY JSON-comparable dictionary.
    """
    label_parts = [f"[bold cyan]{name}[/bold cyan]"]
    type_name = data.get("type_name", "unknown_type")
    value = data.get("value")
    is_null = data.get("is_null", False)
    is_unknown = data.get("is_unknown", False)
    marks = data.get("marks", [])

    label_parts.append(f"([italic green]{type_name}[/italic green])")

    if is_unknown:
        label_parts.append("[bold magenta]unknown[/bold magenta]")
    elif is_null:
        label_parts.append("[dim magenta]null[/dim magenta]")

    if marks:
        label_parts.append(f"marks: {marks}")

    current_branch = tree_node.add(" ".join(label_parts))

    if not is_null and not is_unknown:
        if isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict) and "type_name" in item:
                    build_rich_tree_from_cty_json_comparable(current_branch, item, name=f"[{i}]")
                else:
                    current_branch.add(f"[{i}]: [yellow]{item!r}[/yellow]")
        elif isinstance(value, dict):
            for k, v_item in sorted(value.items()):
                if isinstance(v_item, dict) and "type_name" in v_item:
                    build_rich_tree_from_cty_json_comparable(current_branch, v_item, name=str(k))
                else:
                    current_branch.add(f"{k}: [yellow]{v_item!r}[/yellow]")
        else:
            current_branch.add(f"[yellow]{value!r}[/yellow]")


def build_rich_tree_from_dict(tree_node: Tree, data: dict[str, Any], parent_name: str = "Config Root") -> None:
    """
    Recursively builds a Rich Tree from a generic dictionary.
    """
    if not data:
        tree_node.add(f"[dim italic]{parent_name} (empty)[/dim italic]")
        return

    for key, value in sorted(data.items()):
        if isinstance(value, dict):
            branch = tree_node.add(f"[bold blue]{key}[/bold blue]")
            build_rich_tree_from_dict(branch, value, parent_name=key)
        elif isinstance(value, list):
            branch = tree_node.add(f"[bold blue]{key}[/bold blue] ([italic]list[/italic])")
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    item_branch = branch.add(f"Item {i}")
                    build_rich_tree_from_dict(item_branch, item, parent_name=f"Item {i}")
                else:
                    branch.add(f"[green]{item!r}[/green]")
        else:
            tree_node.add(f"[bold blue]{key}[/bold blue]: [green]{value!r}[/green]")


def print_json(data: Any, indent: int = 2) -> None:
    """Print JSON data with syntax highlighting using Rich."""
    json_str = json.dumps(data, indent=indent, ensure_ascii=False)
    rich_print(f"```json\n{json_str}\n```")


# 🥣🔬🔚

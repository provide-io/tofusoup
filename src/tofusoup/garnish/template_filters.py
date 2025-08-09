#
# tofusoup/garnish/template_filters.py
#
"""Custom Jinja2 filters for documentation generation."""

from typing import Any


def schema_to_markdown(schema: Any, prefix: str = "") -> str:
    """Convert a PvsSchema or a dictionary to markdown documentation."""
    if not schema:
        return ""

    lines = []

    block = schema
    if hasattr(schema, "block"):
        block = schema.block

    # Handle nested blocks
    if hasattr(block, "attributes") and hasattr(block, "block_types"):
        attributes = block.attributes
        nested_blocks = block.block_types

        # Process attributes
        for attr_name, attr_schema in attributes.items():
            attr_type = (
                attr_schema.type.__name__ if hasattr(attr_schema, "type") else "string"
            )
            description = (
                attr_schema.description if hasattr(attr_schema, "description") else ""
            )
            required = (
                attr_schema.required if hasattr(attr_schema, "required") else False
            )
            optional = (
                attr_schema.optional if hasattr(attr_schema, "optional") else False
            )
            computed = (
                attr_schema.computed if hasattr(attr_schema, "computed") else False
            )

            status = []
            if required:
                status.append("Required")
            elif optional:
                status.append("Optional")
            if computed:
                status.append("Computed")

            status_str = ", ".join(status) if status else "Optional"

            lines.append(
                f"- `{prefix}{attr_name}` ({attr_type}) - {description} ({status_str})"
            )

        # Process nested blocks
        for block_name, block_schema in nested_blocks.items():
            lines.append(
                f"- `{prefix}{block_name}` - {block_schema.description if hasattr(block_schema, 'description') else ''}"
            )
            nested_markdown = schema_to_markdown(block_schema, f"{prefix}{block_name}.")
            lines.append(nested_markdown)

    return "\n".join(lines)


def attrs_schema_to_markdown(schema: dict[str, Any], prefix: str = "") -> str:
    """Convert a dictionary from attrs.asdict to markdown documentation."""
    if not schema:
        return ""

    lines = []

    # Handle nested blocks
    if "block" in schema and "attributes" in schema["block"]:
        attributes = schema["block"]["attributes"]
        nested_blocks = schema["block"].get("block_types", [])

        # Process attributes
        for attr_name, attr_schema in attributes.items():
            attr_type = attr_schema.get("type", {}).get("_name", "string")
            description = attr_schema.get("description", "")
            required = attr_schema.get("required", False)
            optional = attr_schema.get("optional", False)
            computed = attr_schema.get("computed", False)

            status = []
            if required:
                status.append("Required")
            elif optional:
                status.append("Optional")
            if computed:
                status.append("Computed")

            status_str = ", ".join(status) if status else "Optional"

            lines.append(
                f"- `{prefix}{attr_name}` ({attr_type}) - {description} ({status_str})"
            )

        # Process nested blocks
        for block in nested_blocks:
            if isinstance(block, dict):
                block_name = block.get("type_name", "")
                lines.append(
                    f"- `{prefix}{block_name}` - {block.get('description', '')}"
                )
                nested_markdown = attrs_schema_to_markdown(
                    block.get("block", {}), f"{prefix}{block_name}."
                )
                lines.append(nested_markdown)

    return "\n".join(lines)


# 🍲🥄📄🪄

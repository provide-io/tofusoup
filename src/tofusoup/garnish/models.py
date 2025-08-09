#
# tofusoup/garnish/models.py
#
"""Data models for documentation generation."""

from typing import Any

from attrs import define, field


@define
class ProviderInfo:
    """Information about a Pyvider provider."""

    name: str
    description: str
    short_name: str = ""
    rendered_name: str = ""
    schema_markdown: str = ""
    has_example: bool = False
    example_file: str = ""

    def __attrs_post_init__(self):
        if not self.short_name:
            self.short_name = self.name
        if not self.rendered_name:
            self.rendered_name = self.name


@define
class ResourceInfo:
    """Information about a resource or data source."""

    name: str
    type: str  # "Resource", "Data Source", or "Function"
    description: str
    schema_markdown: str = ""
    schema: dict[str, Any] | None = None
    has_example: bool = False
    example_file: str = ""
    has_import: bool = False
    import_file: str = ""
    has_import_id_config: bool = False
    import_id_config_file: str = ""
    has_import_identity_config: bool = False
    import_identity_config_file: str = ""
    # Co-located documentation fields
    examples: dict[str, str] = field(factory=dict)
    import_docs: str = ""
    colocated_notes: str = ""
    migration: str = ""


@define
class FunctionInfo:
    """Information about a provider-defined function."""

    name: str
    type: str = "Function"
    description: str = ""
    summary: str = ""
    has_example: bool = False
    example_file: str = ""
    signature_markdown: str = ""
    arguments_markdown: str = ""
    has_variadic: bool = False
    variadic_argument_markdown: str = ""
    # Co-located documentation fields
    examples: dict[str, str] = field(factory=dict)
    import_docs: str = ""
    colocated_notes: str = ""
    migration: str = ""


# 🍲🥄📊🪄

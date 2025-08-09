#
# tofusoup/garnish/template_functions.py
#
"""Custom Jinja2 template functions for .garnish rendering."""

from typing import Any

from jinja2 import BaseLoader, Environment, select_autoescape


class SchemaRenderer:
    """Renders Pyvider schemas to markdown tables."""

    def render_schema(self, schema) -> str:
        """Render schema attributes and blocks to markdown table."""
        if not schema:
            return "No arguments available."

        markdown_parts = []

        # Render main attributes
        if hasattr(schema, "attributes") and schema.attributes:
            markdown_parts.append(self._render_attributes_table(schema.attributes))

        # Render nested blocks
        if hasattr(schema, "blocks") and schema.blocks:
            for block_name, block_schema in schema.blocks.items():
                markdown_parts.append(f"\n### {block_name}\n")
                if hasattr(block_schema, "attributes") and block_schema.attributes:
                    markdown_parts.append(
                        self._render_attributes_table(block_schema.attributes)
                    )

        return (
            "\n".join(markdown_parts) if markdown_parts else "No arguments available."
        )

    def _render_attributes_table(self, attributes: dict[str, Any]) -> str:
        """Render attributes dictionary to markdown table."""
        if not attributes:
            return "No arguments available."

        lines = [
            "| Argument | Type | Required | Description |",
            "|----------|------|----------|-------------|",
        ]

        for attr_name, attr_def in attributes.items():
            # Extract attribute properties
            attr_type = self._format_type(getattr(attr_def, "type", "String"))
            required = self._format_required(attr_def)
            description = getattr(attr_def, "description", "No description available")

            lines.append(
                f"| `{attr_name}` | {attr_type} | {required} | {description} |"
            )

        return "\n".join(lines)

    def _format_type(self, type_info) -> str:
        """Format type information for display."""
        if isinstance(type_info, str):
            return type_info.title()
        elif isinstance(type_info, list) and len(type_info) == 2:
            # Handle complex types like ["list", "string"]
            container, element = type_info
            return f"{container.title()} of {element.title()}"
        else:
            return str(type_info).title()

    def _format_required(self, attr_def) -> str:
        """Format required status for display."""
        if getattr(attr_def, "required", False):
            return "**Yes**"
        elif getattr(attr_def, "computed", False):
            return "No (Computed)"
        else:
            return "No"


class TemplateEngine:
    """Jinja2 template engine with custom functions for .garnish rendering."""

    def __init__(self):
        self.schema_renderer = SchemaRenderer()
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Register custom functions
        self.env.globals.update(
            {
                "schema": self._schema_function,
                "example": self._example_function,
                "include": self._include_function,
                "render": self._render_function,
            }
        )

    def render_template(self, template_content: str, context: dict[str, Any]) -> str:
        """Render template with context."""
        # Store context for custom functions
        self._current_context = context

        try:
            template = self.env.from_string(template_content)
            return template.render(**context)
        finally:
            self._current_context = None

    def _schema_function(self) -> str:
        """{{ schema() }} - Render the component schema as markdown table."""
        if not hasattr(self, "_current_context") or not self._current_context:
            return "<!-- Schema not available -->"

        schema = self._current_context.get("schema")
        if not schema:
            return "<!-- Schema not available -->"

        return self.schema_renderer.render_schema(schema)

    def _example_function(self, example_name: str) -> str:
        """{{ example('name') }} - Render named example in terraform code block."""
        if not hasattr(self, "_current_context") or not self._current_context:
            return f"<!-- Example '{example_name}' not found -->"

        examples = self._current_context.get("examples", {})
        if example_name not in examples:
            return f"<!-- Example '{example_name}' not found -->"

        example_content = examples[example_name]
        return f"```terraform\n{example_content}\n```"

    def _include_function(self, filename: str) -> str:
        """{{ include('filename') }} - Include static partial file."""
        if not hasattr(self, "_current_context") or not self._current_context:
            return f"<!-- Partial '{filename}' not found -->"

        partials = self._current_context.get("partials", {})
        if filename not in partials:
            return f"<!-- Partial '{filename}' not found -->"

        return partials[filename]

    def _render_function(self, filename: str) -> str:
        """{{ render('filename') }} - Render dynamic template partial."""
        if not hasattr(self, "_current_context") or not self._current_context:
            return f"<!-- Partial '{filename}' not found -->"

        partials = self._current_context.get("partials", {})
        if filename not in partials:
            return f"<!-- Partial '{filename}' not found -->"

        # Render the partial as a template with current context
        partial_content = partials[filename]
        try:
            partial_template = self.env.from_string(partial_content)
            return partial_template.render(**self._current_context)
        except Exception as e:
            return f"<!-- Error rendering partial '{filename}': {e} -->"


def create_template_context(component, bundle) -> dict[str, Any]:
    """Create template rendering context from component and bundle."""
    context = {
        "name": bundle.name,
        "type": _format_component_type(bundle.component_type),
        "examples": bundle.load_examples(),
        "partials": bundle.load_partials(),
    }

    # Add schema if available
    try:
        if hasattr(component, "get_schema"):
            context["schema"] = component.get_schema()
        else:
            context["schema"] = None
    except Exception:
        context["schema"] = None

    # Add component-specific context
    if bundle.component_type == "function":
        context.update(_create_function_context(context["schema"]))

    return context


def _format_component_type(component_type: str) -> str:
    """Format component type for display."""
    type_mapping = {
        "resource": "Resource",
        "data_source": "Data Source",
        "function": "Function",
    }
    return type_mapping.get(component_type, component_type.title())


def _create_function_context(schema) -> dict[str, Any]:
    """Create additional context for function components."""
    context = {}

    if schema and hasattr(schema, "parameters"):
        # Add function-specific fields
        context["has_parameters"] = len(schema.parameters) > 0
        context["parameter_count"] = len(schema.parameters)

        if hasattr(schema, "return_type"):
            context["return_type"] = schema.return_type

    return context


# 🍲🥄📄🪄

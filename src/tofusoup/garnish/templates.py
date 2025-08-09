#
# tofusoup/garnish/templates.py
#
"""Template processing and rendering for documentation generation."""

from typing import TYPE_CHECKING

from jinja2 import DictLoader, Environment, select_autoescape

if TYPE_CHECKING:
    from .garnish import GarnishBundle
    from .generator import DocsGenerator


class TemplateProcessor:
    """Handles template generation and rendering."""

    def __init__(self, generator: "DocsGenerator"):
        self.generator = generator

    def generate_missing_templates(self):
        """
        Generate missing template files - now a no-op since we use .garnish bundles.

        This method is kept for compatibility but .garnish directories should contain
        all necessary templates and are discovered automatically.
        """
        print("📄 Using .garnish bundles for templates (no template generation needed)")

    def render_templates(self):
        """Render all templates using garnish bundles to generate documentation."""
        # Ensure output directory exists
        self.generator.output_dir.mkdir(parents=True, exist_ok=True)

        # Discover all garnish bundles
        bundles = self.generator.garnish_discovery.discover_bundles()

        # Render provider index using built-in template
        self._render_provider_index()

        # Render each component with its garnish bundle
        for bundle in bundles:
            self._render_component_from_bundle(bundle)

    def _render_provider_index(self):
        """Render the provider index page using built-in template."""
        if not self.generator.provider_info:
            return

        # Built-in index template
        index_template = """---
page_title: "{{ provider.short_name }} Provider"
description: |-
  {{ provider.description }}
---

# {{ provider.rendered_name }} Provider

{{ provider.description }}

## Example Usage

```terraform
provider "{{ provider.short_name }}" {
  # Configuration options
}
```

## Schema

{{ provider_schema }}
"""

        # Set up Jinja2 environment with built-in template
        env = Environment(
            loader=DictLoader({"index.md.tmpl": index_template}),
            autoescape=select_autoescape(["html", "xml"]),
        )

        template = env.get_template("index.md.tmpl")
        rendered = template.render(
            provider=self.generator.provider_info,
            provider_schema="Provider configuration documentation",  # TODO: implement provider schema
        )

        (self.generator.output_dir / "index.md").write_text(rendered)

    def _render_component_from_bundle(self, bundle: "GarnishBundle"):
        """Render a single component using its garnish bundle."""
        # Load template and assets from bundle
        template_content = bundle.load_main_template()
        if not template_content:
            print(f"⚠️ No main template found for {bundle.name}")
            return

        examples = bundle.load_examples()
        partials = bundle.load_partials()

        # Get component info from generator
        component_info = self._get_component_info(bundle)
        if not component_info:
            print(f"⚠️ No component info found for {bundle.name}")
            return

        # Set up Jinja2 environment with custom functions
        env = Environment(
            loader=DictLoader(
                {
                    "main.tmpl.md": template_content,
                    **partials,  # Include all partials as available templates
                }
            ),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Add custom template functions
        env.globals["schema"] = lambda: component_info.get("schema_markdown", "")
        env.globals["example"] = (
            lambda name: f"```terraform\n{examples.get(name, '')}\n```"
        )
        env.globals["include"] = lambda filename: partials.get(filename, "")
        env.globals["render"] = lambda filename: self._render_partial(
            env, filename, component_info, examples, partials
        )

        # Render the template
        template = env.get_template("main.tmpl.md")

        # Create render context, excluding keys that conflict with template globals
        render_context = {
            k: v for k, v in component_info.items() if k not in ["schema"]
        }
        render_context.update(
            {
                "bundle_name": bundle.name,
                "bundle_type": bundle.component_type.replace("_", " ").title(),
                "examples": examples,
                "partials": partials,
            }
        )

        rendered = template.render(**render_context)

        # Write to output directory
        output_dir = self.generator.output_dir / f"{bundle.component_type}s"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{bundle.name}.md").write_text(rendered)

    def _render_partial(
        self,
        env: Environment,
        filename: str,
        component_info: dict,
        examples: dict,
        partials: dict,
    ) -> str:
        """Render a partial template with full context."""
        try:
            partial_template = env.get_template(filename)
            return partial_template.render(
                name=component_info.get("name", ""),
                type=component_info.get("type", ""),
                schema=component_info.get("schema", {}),
                examples=examples,
                partials=partials,
                **component_info,
            )
        except Exception as e:
            return f"<!-- Error rendering partial {filename}: {e} -->"

    def _get_component_info(self, bundle: "GarnishBundle") -> dict:
        """Get component information based on bundle type and name."""
        # Try both the bundle name as-is and with the pyvider_ prefix
        possible_names = [bundle.name, f"pyvider_{bundle.name}"]

        if bundle.component_type == "resource":
            for name in possible_names:
                resource_info = self.generator.resources.get(name)
                if resource_info:
                    return {
                        "name": resource_info.name,
                        "type": resource_info.type,
                        "description": resource_info.description,
                        "schema": resource_info.schema,
                        "schema_markdown": resource_info.schema_markdown,
                    }
        elif bundle.component_type == "data_source":
            for name in possible_names:
                ds_info = self.generator.data_sources.get(name)
                if ds_info:
                    return {
                        "name": ds_info.name,
                        "type": ds_info.type,
                        "description": ds_info.description,
                        "schema": ds_info.schema,
                        "schema_markdown": ds_info.schema_markdown,
                    }
        elif bundle.component_type == "function":
            for name in possible_names:
                func_info = self.generator.functions.get(name)
                if func_info:
                    return {
                        "name": func_info.name,
                        "description": func_info.description,
                        "summary": func_info.summary,
                        "signature_markdown": func_info.signature_markdown,
                        "arguments_markdown": func_info.arguments_markdown,
                        "variadic_argument_markdown": func_info.variadic_argument_markdown,
                        "has_variadic": func_info.has_variadic,
                    }

        return {}


# 🍲🥄📄🪄

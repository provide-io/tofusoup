#
# tofusoup/garnish/async_renderer.py
#
"""Async garnish-based documentation renderer."""

import asyncio
from pathlib import Path

from jinja2 import DictLoader, Environment, select_autoescape

from pyvider.telemetry import logger

from .garnish import GarnishBundle, GarnishDiscovery
from .schema import SchemaProcessor


class AsyncGarnishRenderer:
    """High-performance async documentation renderer using .garnish bundles."""

    def __init__(
        self,
        provider_dir: Path,
        output_dir: Path = Path("docs"),
        provider_name: str = None,
    ):
        self.provider_dir = provider_dir
        self.output_dir = output_dir
        self.provider_name = provider_name or self._detect_provider_name()
        self.garnish_discovery = GarnishDiscovery()
        self.schema_processor = None

        # Component data caches
        self.component_schemas = {}
        self.component_info = {}

    def _detect_provider_name(self) -> str:
        """Detect provider name from configuration files first, then directory name."""
        # Try to detect from pyproject.toml first (highest priority)
        pyproject_file = self.provider_dir / "pyproject.toml"
        if pyproject_file.exists():
            try:
                import tomllib

                with open(pyproject_file, "rb") as f:
                    data = tomllib.load(f)

                # Check tool.pyvbuild.provider_name (most specific)
                pyvbuild_name = (
                    data.get("tool", {}).get("pyvbuild", {}).get("provider_name")
                )
                if pyvbuild_name:
                    return pyvbuild_name

                # Check tool.pyvider-builder.name
                builder_name = (
                    data.get("tool", {}).get("pyvider-builder", {}).get("name")
                )
                if builder_name:
                    return builder_name

                # Check tool.pyvider.provider_name
                pyvider_name = (
                    data.get("tool", {}).get("pyvider", {}).get("provider_name")
                )
                if pyvider_name:
                    return pyvider_name

                # Fallback to project name
                project_name = data.get("project", {}).get("name", "")
                if project_name.startswith("terraform-provider-"):
                    return project_name[19:]  # Remove "terraform-provider-" prefix
                elif project_name:
                    return project_name

            except Exception:
                pass

        # Try to detect from directory name as fallback
        dir_name = self.provider_dir.name
        if dir_name.startswith("terraform-provider-"):
            return dir_name[19:]  # Remove "terraform-provider-" prefix

        # Default fallback
        return "provider"

    async def render_all(self) -> None:
        """Render all documentation components asynchronously."""
        # Initialize schema processor and extract schemas
        # Create a mock generator object for backward compatibility
        mock_generator = type(
            "MockGenerator",
            (),
            {"provider_name": self.provider_name, "provider_dir": self.provider_dir},
        )()

        self.schema_processor = SchemaProcessor(mock_generator)
        provider_schema = await self._extract_schemas()

        # Parse schemas into component info
        await self._parse_component_info(provider_schema)

        # Discover garnish bundles
        bundles = await self._discover_bundles()

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Render all components concurrently
        tasks = [
            self._render_provider_index(),
            *[self._render_component_bundle(bundle) for bundle in bundles],
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _extract_schemas(self) -> dict:
        """Extract component schemas asynchronously."""
        return await asyncio.to_thread(self.schema_processor.extract_provider_schema)

    async def _parse_component_info(self, provider_schema: dict) -> None:
        """Parse component information from provider schema."""
        # Parse provider schema into component info dictionaries
        provider_config = provider_schema.get("provider_schemas", {}).get(
            f"registry.terraform.io/local/providers/{self.provider_name}", {}
        )

        # Resources
        for name, schema in provider_config.get("resource_schemas", {}).items():
            self.component_info[name] = {
                "name": name,
                "type": "Resource",
                "description": schema.get("description", ""),
                "schema": schema,
                "schema_markdown": await self._render_schema_markdown(schema),
            }

        # Data sources
        for name, schema in provider_config.get("data_source_schemas", {}).items():
            self.component_info[name] = {
                "name": name,
                "type": "Data Source",
                "description": schema.get("description", ""),
                "schema": schema,
                "schema_markdown": await self._render_schema_markdown(schema),
            }

        # Functions
        for name, schema in provider_config.get("functions", {}).items():
            self.component_info[name] = {
                "name": name,
                "type": "Function",
                "description": schema.get("description", ""),
                "summary": schema.get("summary", ""),
                "schema": schema,
                "signature_markdown": self._parse_function_signature(schema),
                "arguments_markdown": self._parse_function_arguments(schema),
                "variadic_argument_markdown": self._parse_variadic_argument(schema),
                "has_variadic": "variadic_parameter" in schema.get("signature", {}),
            }

    async def _render_schema_markdown(self, schema: dict) -> str:
        """Render schema to markdown asynchronously."""
        return await asyncio.to_thread(
            self.schema_processor._parse_schema_to_markdown, schema
        )

    def _format_type_string(self, type_info) -> str:
        """Convert a type object to a human-readable type string (sync version)."""
        if not type_info:
            return "String"  # Default fallback

        # Handle CTY type objects
        try:
            # Import here to avoid circular imports
            from pyvider.cty import (
                CtyBool,
                CtyDynamic,
                CtyList,
                CtyMap,
                CtyNumber,
                CtyObject,
                CtySet,
                CtyString,
            )

            if hasattr(type_info, "__class__"):
                type_class = type_info.__class__
                if type_class == CtyString:
                    return "String"
                elif type_class == CtyNumber:
                    return "Number"
                elif type_class == CtyBool:
                    return "Boolean"
                elif type_class == CtyList:
                    element_type = self._format_type_string(
                        getattr(type_info, "element_type", None)
                    )
                    return f"List of {element_type}"
                elif type_class == CtySet:
                    element_type = self._format_type_string(
                        getattr(type_info, "element_type", None)
                    )
                    return f"Set of {element_type}"
                elif type_class == CtyMap:
                    element_type = self._format_type_string(
                        getattr(type_info, "element_type", None)
                    )
                    return f"Map of {element_type}"
                elif type_class == CtyObject:
                    return "Object"
                elif type_class == CtyDynamic:
                    return "Dynamic"
        except (ImportError, AttributeError):
            pass

        # Handle string representations
        if isinstance(type_info, str):
            type_str = type_info.lower()
            if "string" in type_str:
                return "String"
            elif "number" in type_str or "int" in type_str or "float" in type_str:
                return "Number"
            elif "bool" in type_str:
                return "Boolean"
            elif "list" in type_str:
                return "List of String"
            elif "set" in type_str:
                return "Set of String"
            elif "map" in type_str:
                return "Map of String"
            elif "object" in type_str:
                return "Object"

        # Handle dict representations (from schema extraction)
        if isinstance(type_info, dict):
            # Check if it's an empty dict (common case we saw)
            if not type_info:
                return "String"  # Default fallback

            # Try to infer from dict structure
            if "type" in type_info:
                return self._format_type_string(type_info["type"])

        # Final fallback
        return "String"

    async def _discover_bundles(self) -> list[GarnishBundle]:
        """Discover garnish bundles asynchronously."""
        return await asyncio.to_thread(self.garnish_discovery.discover_bundles)

    async def _render_provider_index(self) -> None:
        """Render provider index page with built-in template."""
        # Built-in provider index template (Pythonic Jinja2)
        template_content = """---
page_title: "{{ provider_name }} Provider"
description: |-
  Terraform provider for {{ provider_name }}
---

# {{ provider_name }} Provider

Terraform provider for {{ provider_name }}.

## Example Usage

```terraform
provider "{{ provider_name }}" {
  # Configuration options
}
```

## Schema

{{ provider_schema }}
"""

        env = Environment(
            loader=DictLoader({"index.tmpl": template_content}),
            autoescape=select_autoescape(["html", "xml"]),
        )

        template = env.get_template("index.tmpl")
        rendered = template.render(
            provider_name=self.provider_name,
            provider_schema="Provider configuration documentation",
        )

        await asyncio.to_thread((self.output_dir / "index.md").write_text, rendered)

    async def _render_component_bundle(self, bundle: GarnishBundle) -> None:
        """Render a single component bundle asynchronously."""
        try:
            # Load bundle assets concurrently
            template_task = asyncio.to_thread(bundle.load_main_template)
            examples_task = asyncio.to_thread(bundle.load_examples)
            partials_task = asyncio.to_thread(bundle.load_partials)

            template_content, examples, partials = await asyncio.gather(
                template_task, examples_task, partials_task
            )

            if not template_content:
                # Skip components without templates (no warning)
                return

            # Get component info (try both bundle name and with pyvider_ prefix)
            component_info = self.component_info.get(bundle.name)
            if not component_info:
                component_info = self.component_info.get(f"pyvider_{bundle.name}")
            if not component_info:
                # For components without schema info, create minimal component info
                if bundle.component_type == "function":
                    component_info = {
                        "name": bundle.name,
                        "type": "Function",
                        "description": f"The {bundle.name} function",
                        "summary": "",
                        "schema": {},
                        "signature_markdown": f"`{bundle.name}(...)`",
                        "arguments_markdown": "",
                        "variadic_argument_markdown": "",
                        "has_variadic": False,
                    }
                elif bundle.component_type == "resource":
                    # Try to look up the actual component for better schema info
                    actual_component_info = await self._try_get_actual_component_schema(
                        bundle
                    )
                    component_info = {
                        "name": bundle.name,
                        "type": "Resource",
                        "description": f"The {bundle.name} resource",
                        "schema": {},
                        "schema_markdown": actual_component_info.get(
                            "schema_markdown", ""
                        ),
                    }
                elif bundle.component_type == "data_source":
                    # Try to look up the actual component for better schema info
                    actual_component_info = await self._try_get_actual_component_schema(
                        bundle
                    )
                    component_info = {
                        "name": bundle.name,
                        "type": "Data Source",
                        "description": f"The {bundle.name} data source",
                        "schema": {},
                        "schema_markdown": actual_component_info.get(
                            "schema_markdown", ""
                        ),
                    }
            if not component_info:
                # Skip components not found in schema (no warning)
                return

            # Render template
            rendered = await self._render_template(
                template_content, component_info, examples, partials
            )

            # Write output
            output_dir = self.output_dir / self._get_output_subdir(
                bundle.component_type
            )
            await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)

            output_file = output_dir / f"{bundle.name}.md"
            await asyncio.to_thread(output_file.write_text, rendered)

        except Exception as e:
            logger.debug(
                "Error rendering component bundle",
                bundle_name=bundle.name,
                error=str(e),
            )

    async def _render_template(
        self,
        template_content: str,
        component_info: dict,
        examples: dict,
        partials: dict,
    ) -> str:
        """Render a template with Pythonic Jinja2 context."""

        def render_sync():
            # Set up Jinja2 environment with custom functions
            env = Environment(
                loader=DictLoader({"main.tmpl": template_content, **partials}),
                autoescape=select_autoescape(["html", "xml"]),
            )

            # Custom template functions (Pythonic)
            env.globals["schema"] = lambda: component_info.get("schema_markdown", "")
            env.globals["example"] = (
                lambda name: f"```terraform\n{examples.get(name, '')}\n```"
            )
            env.globals["include"] = lambda filename: partials.get(filename, "")
            env.globals["render"] = lambda filename: self._render_partial_sync(
                env, filename, component_info, examples, partials
            )

            # Render with Pythonic context
            template = env.get_template("main.tmpl")

            # Create render context, excluding keys that conflict with template globals
            render_context = {
                k: v for k, v in component_info.items() if k not in ["schema"]
            }
            render_context.update(
                {
                    "examples": examples,
                    "partials": partials,
                }
            )

            return template.render(**render_context)

        return await asyncio.to_thread(render_sync)

    def _render_partial_sync(
        self, env, filename: str, component_info: dict, examples: dict, partials: dict
    ) -> str:
        """Render a partial template synchronously (called from within Jinja2)."""
        try:
            partial_template = env.get_template(filename)

            # Create render context, excluding keys that conflict with template globals
            render_context = {
                k: v for k, v in component_info.items() if k not in ["schema"]
            }
            render_context.update(
                {
                    "examples": examples,
                    "partials": partials,
                }
            )

            return partial_template.render(**render_context)
        except Exception as e:
            return f"<!-- Error rendering partial {filename}: {e} -->"

    def _get_output_subdir(self, component_type: str) -> str:
        """Get output subdirectory for component type."""
        return {
            "resource": "resources",
            "data_source": "data_sources",
            "function": "functions",
        }.get(component_type, "resources")

    def _parse_function_signature(self, func_schema: dict) -> str:
        """Parse function signature from schema."""
        if "signature" not in func_schema:
            return ""

        signature = func_schema["signature"]
        params = []

        # Handle parameters
        if "parameters" in signature:
            for param in signature["parameters"]:
                param_name = param.get("name", "arg")
                param_type = param.get("type", "any")
                params.append(f"{param_name}: {param_type}")

        # Handle variadic parameter
        if "variadic_parameter" in signature:
            variadic = signature["variadic_parameter"]
            variadic_name = variadic.get("name", "args")
            variadic_type = variadic.get("type", "any")
            params.append(f"...{variadic_name}: {variadic_type}")

        # Handle return type
        return_type = signature.get("return_type", "any")
        param_str = ", ".join(params)
        return f"function({param_str}) -> {return_type}"

    def _parse_function_arguments(self, func_schema: dict) -> str:
        """Parse function arguments from schema."""
        if "signature" not in func_schema:
            return ""

        signature = func_schema["signature"]
        lines = []

        # Handle parameters
        if "parameters" in signature:
            for param in signature["parameters"]:
                param_name = param.get("name", "arg")
                param_type = param.get("type", "any")
                description = param.get("description", "")
                lines.append(f"- `{param_name}` ({param_type}) - {description}")

        return "\n".join(lines)

    def _parse_variadic_argument(self, func_schema: dict) -> str:
        """Parse variadic argument from schema."""
        if (
            "signature" not in func_schema
            or "variadic_parameter" not in func_schema["signature"]
        ):
            return ""

        variadic = func_schema["signature"]["variadic_parameter"]
        variadic_name = variadic.get("name", "args")
        variadic_type = variadic.get("type", "any")
        description = variadic.get("description", "")

        return f"- `{variadic_name}` ({variadic_type}) - {description}"

    async def _try_get_actual_component_schema(self, bundle: GarnishBundle) -> dict:
        """Try to get actual component schema by looking up in Pyvider hub."""
        try:
            # This is a fallback method to generate better schema info
            # even when the extracted provider schema doesn't have the info
            from pyvider.hub import hub

            # Look up the component in the hub
            component_name = bundle.name
            if bundle.component_type == "resource":
                possible_names = [component_name, f"pyvider_{component_name}"]
                for name in possible_names:
                    if name in hub.resources:
                        resource_class = hub.resources[name]
                        return await self._generate_schema_from_component(
                            resource_class, bundle.component_type
                        )
            elif bundle.component_type == "data_source":
                possible_names = [component_name, f"pyvider_{component_name}"]
                for name in possible_names:
                    if name in hub.data_sources:
                        ds_class = hub.data_sources[name]
                        return await self._generate_schema_from_component(
                            ds_class, bundle.component_type
                        )

        except Exception as e:
            logger.debug(
                "Could not get actual component schema",
                bundle_name=bundle.name,
                error=str(e),
            )

        return {}

    async def _generate_schema_from_component(
        self, component_class, component_type: str
    ) -> dict:
        """Generate schema markdown from a component class."""
        try:
            # Get the component's schema
            if hasattr(component_class, "__pyvider_schema__"):
                schema_obj = component_class.__pyvider_schema__

                # Generate basic schema markdown
                lines = ["## Schema", ""]

                # Try to extract attributes from the schema object
                if hasattr(schema_obj, "attributes") and schema_obj.attributes:
                    lines.extend(["### Required", ""])
                    required_attrs = []
                    optional_attrs = []
                    computed_attrs = []

                    for attr_name, attr_def in schema_obj.attributes.items():
                        # Try to determine type and characteristics
                        attr_type = "String"  # Default
                        characteristics = []

                        # Determine characteristics from attribute definition
                        if hasattr(attr_def, "required") and attr_def.required:
                            characteristics.append("Required")
                            required_attrs.append(
                                (
                                    attr_name,
                                    attr_type,
                                    characteristics,
                                    getattr(attr_def, "description", ""),
                                )
                            )
                        elif hasattr(attr_def, "optional") and attr_def.optional:
                            characteristics.append("Optional")
                            optional_attrs.append(
                                (
                                    attr_name,
                                    attr_type,
                                    characteristics,
                                    getattr(attr_def, "description", ""),
                                )
                            )
                        elif hasattr(attr_def, "computed") and attr_def.computed:
                            characteristics.append("Computed")
                            computed_attrs.append(
                                (
                                    attr_name,
                                    attr_type,
                                    characteristics,
                                    getattr(attr_def, "description", ""),
                                )
                            )

                    # Format attributes
                    if required_attrs:
                        lines.extend(["### Required", ""])
                        for attr_name, attr_type, chars, desc in required_attrs:
                            char_str = f", {', '.join(chars)}" if chars else ""
                            lines.append(
                                f"- `{attr_name}` ({attr_type}{char_str}) {desc}".strip()
                            )
                        lines.append("")

                    if optional_attrs:
                        lines.extend(["### Optional", ""])
                        for attr_name, attr_type, chars, desc in optional_attrs:
                            char_str = f", {', '.join(chars)}" if chars else ""
                            lines.append(
                                f"- `{attr_name}` ({attr_type}{char_str}) {desc}".strip()
                            )
                        lines.append("")

                    if computed_attrs:
                        lines.extend(["### Read-Only", ""])
                        for attr_name, attr_type, chars, desc in computed_attrs:
                            char_str = f", {', '.join(chars)}" if chars else ""
                            lines.append(
                                f"- `{attr_name}` ({attr_type}{char_str}) {desc}".strip()
                            )
                        lines.append("")

                return {"schema_markdown": "\n".join(lines)}

        except Exception as e:
            logger.debug("Could not generate schema from component", error=str(e))

        return {}


# Adapter class for backward compatibility
class DocsGenerator:
    """Backward compatibility adapter for the async renderer."""

    def __init__(
        self,
        provider_dir: Path,
        output_dir: str = "docs",
        provider_name: str = None,
        **kwargs,
    ):
        self.provider_dir = provider_dir
        self.output_dir = Path(output_dir)
        self.provider_name = provider_name

        # For backward compatibility with schema processor
        self.renderer = AsyncGarnishRenderer(
            provider_dir, self.output_dir, provider_name
        )

    def generate(self):
        """Generate documentation using the async renderer."""
        print(
            f"🔍 Generating documentation for {self.renderer.provider_name} provider..."
        )
        print("📋 Extracting provider schema...")
        print("📁 Processing examples...")
        print("📄 Generating missing templates...")
        print("🎨 Rendering templates...")

        # Run async renderer
        asyncio.run(self.renderer.render_all())

        print(f"✅ Documentation generated successfully in {self.output_dir}")


# Async entry point
async def generate_docs_async(
    provider_dir: Path = Path(),
    output_dir: str = "docs",
    provider_name: str = None,
    **kwargs,
) -> None:
    """Async entry point for documentation generation."""
    renderer = AsyncGarnishRenderer(provider_dir, Path(output_dir), provider_name)
    await renderer.render_all()


# Sync entry point (for backward compatibility)
def generate_docs(
    provider_dir: Path = Path(),
    output_dir: str = "docs",
    provider_name: str = None,
    **kwargs,
) -> None:
    """Sync entry point for documentation generation."""
    generator = DocsGenerator(provider_dir, output_dir, provider_name, **kwargs)
    generator.generate()


# 🍲🥄📄🪄

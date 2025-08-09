#
# tofusoup/garnish/schema.py
#
"""Schema extraction and processing for documentation generation."""

import json
from pathlib import Path
import shutil
import subprocess
from typing import TYPE_CHECKING, Any

import attrs

from pyvider.hub import ComponentDiscovery, hub

from .models import FunctionInfo, ProviderInfo, ResourceInfo

if TYPE_CHECKING:
    from .generator import DocsGenerator


class SchemaProcessor:
    """Handles schema extraction and processing."""

    def __init__(self, generator: "DocsGenerator"):
        self.generator = generator

    def extract_provider_schema(self) -> dict[str, Any]:
        """Extract provider schema using Pyvider's component discovery."""
        import asyncio

        return asyncio.run(self._extract_schema_via_discovery())

    async def _extract_schema_via_discovery(self) -> dict[str, Any]:
        """Extract schema by discovering components and inspecting their schemas."""
        print("🔍 Discovering components via Pyvider hub...")
        discovery = ComponentDiscovery(hub)
        await discovery.discover_all()

        components = hub.list_components()

        provider_schema = {
            "provider_schemas": {
                f"registry.terraform.io/local/providers/{self.generator.provider_name}": {
                    "provider": self._get_provider_schema(
                        components.get("provider", {})
                    ),
                    "resource_schemas": self._get_component_schemas(
                        components.get("resource", {})
                    ),
                    "data_source_schemas": self._get_component_schemas(
                        components.get("data_source", {})
                    ),
                    "functions": self._get_function_schemas(
                        components.get("function", {})
                    ),
                }
            }
        }
        return provider_schema

    def _get_provider_schema(self, providers: dict[str, Any]) -> dict[str, Any]:
        if not providers:
            return {"block": {"attributes": {}}}
        provider_component = next(iter(providers.values()))
        if hasattr(provider_component, "get_schema"):
            schema = provider_component.get_schema()
            return attrs.asdict(schema)
        return {"block": {"attributes": {}}}

    def _get_component_schemas(self, components: dict[str, Any]) -> dict[str, Any]:
        """Get schemas for resources or data sources."""
        schemas = {}
        for name, component in components.items():
            if hasattr(component, "get_schema"):
                schema = component.get_schema()
                schemas[name] = attrs.asdict(schema)
            elif hasattr(component, "__pyvider_schema__"):
                schema_attr = component.__pyvider_schema__
                schemas[name] = schema_attr
        return schemas

    def _get_function_schemas(self, functions: dict[str, Any]) -> dict[str, Any]:
        """Get schemas for functions."""
        schemas = {}
        for name, func in functions.items():
            if hasattr(func, "get_schema"):
                schema = func.get_schema()
                schemas[name] = attrs.asdict(schema)
            elif hasattr(func, "__pyvider_schema__"):
                schemas[name] = func.__pyvider_schema__
        return schemas

    def _extract_schema_via_terraform(self) -> dict[str, Any]:
        """Fallback: Extract schema by building provider and using Terraform CLI."""
        # Build the provider binary
        print(f"Building provider in {self.generator.provider_dir}")
        build_result = subprocess.run(
            ["python", "-m", "build"],
            cwd=self.generator.provider_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if build_result.returncode != 0:
            print("---STDOUT---")
            print(build_result.stdout)
            print("---STDERR---")
            print(build_result.stderr)
            build_result.check_returncode()

        # Find the built provider binary
        provider_binary = self._find_provider_binary()

        # Create a temporary directory for Terraform operations
        temp_dir = self.generator.provider_dir / ".pyvbuild_temp"
        temp_dir.mkdir(exist_ok=True)

        try:
            # Create basic Terraform configuration
            tf_config = f'''
terraform {{
  required_providers {{
    {self.generator.provider_name} = {{
      source = "local/providers/{self.generator.provider_name}"
    }}
  }}
}}

provider "{self.generator.provider_name}" {{}}
'''

            tf_file = temp_dir / "main.tf"
            tf_file.write_text(tf_config)

            # Initialize Terraform
            subprocess.run(
                ["terraform", "init"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            # Extract schema
            schema_result = subprocess.run(
                ["terraform", "providers", "schema", "-json"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            schema_data = json.loads(schema_result.stdout)
            return schema_data

        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _find_provider_binary(self) -> Path:
        """Find the provider binary after building."""
        # Look for the provider binary in common locations
        binary_paths = [
            self.generator.provider_dir / "terraform-provider-*",
            self.generator.provider_dir / "dist" / "terraform-provider-*",
            self.generator.provider_dir / "bin" / "terraform-provider-*",
        ]

        import glob

        for pattern in binary_paths:
            matches = glob.glob(str(pattern))
            if matches:
                return Path(matches[0])

        raise FileNotFoundError(
            f"Could not find provider binary for {self.generator.provider_name}"
        )

    def _parse_function_signature(self, func_schema: dict[str, Any]) -> str:
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

    def _parse_function_arguments(self, func_schema: dict[str, Any]) -> str:
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

    def _parse_variadic_argument(self, func_schema: dict[str, Any]) -> str:
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

    def parse_provider_schema(self):
        """Parse extracted provider schema into internal structures."""
        schema = self.generator.provider_schema
        if not schema:
            return

        # Create provider info
        provider_schema = schema.get("provider_schemas", {}).get(
            f"registry.terraform.io/local/providers/{self.generator.provider_name}", {}
        )
        provider_config_schema = provider_schema.get("provider", {})

        self.generator.provider_info = ProviderInfo(
            name=self.generator.provider_name,
            description=provider_config_schema.get(
                "description", f"Terraform provider for {self.generator.provider_name}"
            ),
            short_name=self.generator.provider_name,
            rendered_name=self.generator.rendered_provider_name,
        )

        # Process resources
        resources = provider_schema.get("resource_schemas", {})
        if isinstance(resources, tuple):
            resources = {}
        for resource_name, resource_schema in resources.items():
            if self.generator.ignore_deprecated and resource_schema.get(
                "deprecated", False
            ):
                continue

            schema_markdown = self._parse_schema_to_markdown(resource_schema)

            self.generator.resources[resource_name] = ResourceInfo(
                name=resource_name,
                type="Resource",
                description=resource_schema.get("description", ""),
                schema_markdown=schema_markdown,
                schema=resource_schema,
            )

        # Process data sources
        data_sources = provider_schema.get("data_source_schemas", {})
        for ds_name, ds_schema in data_sources.items():
            if self.generator.ignore_deprecated and ds_schema.get("deprecated", False):
                continue

            schema_markdown = self._parse_schema_to_markdown(ds_schema)

            self.generator.data_sources[ds_name] = ResourceInfo(
                name=ds_name,
                type="Data Source",
                description=ds_schema.get("description", ""),
                schema_markdown=schema_markdown,
                schema=ds_schema,
            )

        # Process functions
        functions = provider_schema.get("functions", {})
        for func_name, func_schema in functions.items():
            signature_markdown = self._parse_function_signature(func_schema)
            arguments_markdown = self._parse_function_arguments(func_schema)
            variadic_markdown = self._parse_variadic_argument(func_schema)

            self.generator.functions[func_name] = FunctionInfo(
                name=func_name,
                description=func_schema.get("description", ""),
                summary=func_schema.get("summary", ""),
                signature_markdown=signature_markdown,
                arguments_markdown=arguments_markdown,
                has_variadic="variadic_parameter" in func_schema.get("signature", {}),
                variadic_argument_markdown=variadic_markdown,
            )

    def _parse_schema_to_markdown(self, schema: dict[str, Any]) -> str:
        """Parse a schema object into markdown documentation."""
        if not schema:
            return ""

        # Extract block information
        block = schema.get("block", {})
        if not block:
            return ""

        markdown_lines = []

        # Handle attributes
        attributes = block.get("attributes", {})
        if attributes:
            markdown_lines.append("## Arguments\n")
            for attr_name, attr_spec in attributes.items():
                description = attr_spec.get("description", "")
                attr_type_raw = attr_spec.get("type", {})
                attr_type = self._format_type_string(attr_type_raw)
                required = attr_spec.get("required", False)
                optional = attr_spec.get("optional", False)
                computed = attr_spec.get("computed", False)

                # Determine characteristics
                characteristics = []
                if required:
                    characteristics.append("Required")
                elif optional:
                    characteristics.append("Optional")
                elif computed:
                    characteristics.append("Computed")

                # Format like tfplugindocs: (Type, Characteristics)
                if characteristics:
                    type_text = f"({attr_type}, {', '.join(characteristics)})"
                else:
                    type_text = f"({attr_type})"

                markdown_lines.append(
                    f"- `{attr_name}` {type_text} {description}".strip()
                )

            markdown_lines.append("")

        # Handle nested blocks
        nested_blocks = block.get("block_types", {})
        if nested_blocks and isinstance(nested_blocks, dict):
            markdown_lines.append("## Blocks\n")
            for block_name, block_spec in nested_blocks.items():
                description = block_spec.get("description", "")
                nesting_mode = block_spec.get("nesting_mode", "single")

                markdown_lines.append(f"### {block_name}")
                if description:
                    markdown_lines.append(f"\n{description}\n")

                # Handle block attributes
                block_attrs = block_spec.get("block", {}).get("attributes", {})
                if block_attrs:
                    for attr_name, attr_spec in block_attrs.items():
                        attr_description = attr_spec.get("description", "")
                        attr_type = attr_spec.get("type", "unknown")
                        required = attr_spec.get("required", False)
                        optional = attr_spec.get("optional", False)
                        computed = attr_spec.get("computed", False)

                        if required:
                            req_text = " (Required)"
                        elif optional:
                            req_text = " (Optional)"
                        elif computed:
                            req_text = " (Computed)"
                        else:
                            req_text = ""

                        markdown_lines.append(
                            f"- `{attr_name}` ({attr_type}){req_text} - {attr_description}"
                        )

                markdown_lines.append("")

        return "\n".join(markdown_lines)

    def _format_type_string(self, type_info: Any) -> str:
        """Convert a type object to a human-readable type string."""
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


# 🍲🥄📊🪄

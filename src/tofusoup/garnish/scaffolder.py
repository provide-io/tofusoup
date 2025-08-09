#
# tofusoup/garnish/scaffolder.py
#
"""Scaffolding system for creating missing .garnish directories."""

import asyncio
from pathlib import Path

from pyvider.hub import ComponentDiscovery, hub

from .garnish import GarnishDiscovery


class GarnishScaffolder:
    """Creates missing .garnish directories for components."""

    def __init__(self):
        self.garnish_discovery = GarnishDiscovery()

    async def scaffold_missing(
        self, component_types: list[str] = None
    ) -> dict[str, int]:
        """
        Scaffold missing .garnish directories for discovered components.

        Returns a dictionary with counts of scaffolded components by type.
        """
        # Discover all components via hub
        discovery = ComponentDiscovery(hub)
        await discovery.discover_all()
        components = hub.list_components()

        # Find existing garnish bundles
        existing_bundles = await asyncio.to_thread(
            self.garnish_discovery.discover_bundles
        )
        existing_names = {bundle.name for bundle in existing_bundles}

        # Track scaffolding results
        scaffolded = {"resource": 0, "data_source": 0, "function": 0}

        # Filter by component types if specified
        target_types = component_types or ["resource", "data_source", "function"]

        # Scaffold missing components
        for component_type in target_types:
            if component_type in components:
                for name, component_class in components[component_type].items():
                    if name not in existing_names:
                        success = await self._scaffold_component(
                            name, component_type, component_class
                        )
                        if success:
                            scaffolded[component_type] += 1

        return scaffolded

    async def _scaffold_component(
        self, name: str, component_type: str, component_class
    ) -> bool:
        """Scaffold a single component's .garnish directory."""
        try:
            # Find the component's source file location
            source_file = await self._find_component_source(component_class)
            if not source_file:
                print(f"⚠️ Could not find source file for {name}")
                return False

            # Create .garnish directory
            garnish_dir = source_file.parent / f"{source_file.stem}.garnish"
            docs_dir = garnish_dir / "docs"
            examples_dir = garnish_dir / "examples"

            await asyncio.to_thread(docs_dir.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(examples_dir.mkdir, parents=True, exist_ok=True)

            # Create main template
            template_content = await self._generate_template_content(
                name, component_type, component_class
            )
            template_file = docs_dir / f"{name}.tmpl.md"
            await asyncio.to_thread(template_file.write_text, template_content)

            # Create example file
            example_content = await self._generate_example_content(name, component_type)
            example_file = examples_dir / "example.tf"
            await asyncio.to_thread(example_file.write_text, example_content)

            print(f"✅ Scaffolded {component_type}: {name}")
            return True

        except Exception as e:
            print(f"❌ Failed to scaffold {name}: {e}")
            return False

    async def _find_component_source(self, component_class) -> Path:
        """Find the source file for a component class."""
        try:
            import inspect

            source_file = inspect.getfile(component_class)
            return Path(source_file)
        except Exception:
            return None

    async def _generate_template_content(
        self, name: str, component_type: str, component_class
    ) -> str:
        """Generate template content based on component type."""
        # Get component description if available
        description = (
            getattr(component_class, "__doc__", "")
            or f"Terraform {component_type} for {name}"
        )
        description = description.strip().split("\n")[0]  # First line only

        if component_type == "resource":
            return self._resource_template(name, description)
        elif component_type == "data_source":
            return self._data_source_template(name, description)
        elif component_type == "function":
            return self._function_template(name, description)
        else:
            return self._generic_template(name, description, component_type)

    def _resource_template(self, name: str, description: str) -> str:
        """Generate resource template content."""
        return f"""---
page_title: "Resource: {name}"
description: |-
  {description}
---

# {name} (Resource)

{description}

## Example Usage

{{{{ example("example") }}}}

## Argument Reference

{{{{ schema() }}}}

## Import

```bash
terraform import {name}.example <id>
```
"""

    def _data_source_template(self, name: str, description: str) -> str:
        """Generate data source template content."""
        return f"""---
page_title: "Data Source: {name}"
description: |-
  {description}
---

# {name} (Data Source)

{description}

## Example Usage

{{{{ example("example") }}}}

## Argument Reference

{{{{ schema() }}}}
"""

    def _function_template(self, name: str, description: str) -> str:
        """Generate function template content."""
        return f"""---
page_title: "Function: {name}"
description: |-
  {description}
---

# {name} (Function)

{description}

## Example Usage

{{{{ example("example") }}}}

## Signature

`{{{{ signature_markdown }}}}`

## Arguments

{{{{ arguments_markdown }}}}

{{% if has_variadic %}}
## Variadic Arguments

{{{{ variadic_argument_markdown }}}}
{{% endif %}}
"""

    def _generic_template(
        self, name: str, description: str, component_type: str
    ) -> str:
        """Generate generic template content."""
        return f"""---
page_title: "{component_type.title()}: {name}"
description: |-
  {description}
---

# {name} ({component_type.title()})

{description}

## Example Usage

{{{{ example("example") }}}}

## Schema

{{{{ schema() }}}}
"""

    async def _generate_example_content(self, name: str, component_type: str) -> str:
        """Generate example Terraform content."""
        if component_type == "resource":
            return f'''resource "{name}" "example" {{
  # Configuration options here
}}

output "example_id" {{
  description = "The ID of the {name} resource"
  value       = {name}.example.id
}}
'''
        elif component_type == "data_source":
            return f'''data "{name}" "example" {{
  # Configuration options here
}}

output "example_data" {{
  description = "Data from {name}"
  value       = data.{name}.example
}}
'''
        elif component_type == "function":
            return f"""locals {{
  example_result = {name}(
    # Function arguments here
  )
}}

output "function_result" {{
  description = "Result of {name} function"  
  value       = local.example_result
}}
"""
        else:
            return f"""# Example usage for {name}
# Add your Terraform configuration here
"""


# Async entry point
async def scaffold_missing_garnish(component_types: list[str] = None) -> dict[str, int]:
    """Scaffold missing .garnish directories."""
    scaffolder = GarnishScaffolder()
    return await scaffolder.scaffold_missing(component_types)


# Sync entry point
def scaffold_garnish(component_types: list[str] = None) -> dict[str, int]:
    """Sync entry point for scaffolding."""
    return asyncio.run(scaffold_missing_garnish(component_types))


# 🍲🥄📄🪄

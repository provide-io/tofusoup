#
# tofusoup/garnish/garnish_renderer.py
#
"""Garnish template rendering system."""

import importlib
from pathlib import Path

from .garnish import GarnishBundle, GarnishDiscovery
from .template_functions import TemplateEngine, create_template_context


class GarnishRenderer:
    """Renders .garnish bundles to markdown documentation."""

    def __init__(
        self,
        output_dir: Path | None = None,
        component_types: list[str] | None = None,
    ):
        self.output_dir = output_dir or Path("docs")
        self.component_types = component_types
        self.discovery = GarnishDiscovery()
        self.template_engine = TemplateEngine()

    def render_all(self) -> list[Path]:
        """Render all discovered .garnish bundles to output directory."""
        output_files = []

        try:
            # Discover all bundles
            bundles = self.discovery.discover_bundles()

            # Filter by component types if specified
            if self.component_types:
                bundles = [
                    b for b in bundles if b.component_type in self.component_types
                ]

            for bundle in bundles:
                try:
                    output_file = self._render_bundle(bundle)
                    if output_file:
                        output_files.append(output_file)
                except Exception as e:
                    print(f"Error rendering bundle {bundle.name}: {e}")
                    continue

        except Exception as e:
            print(f"Error discovering bundles: {e}")
            return []

        return output_files

    def render_component(self, component_name: str) -> Path | None:
        """Render a single component by name."""
        try:
            bundles = self.discovery.discover_bundles()

            # Find the specific bundle
            target_bundle = None
            for bundle in bundles:
                if bundle.name == component_name:
                    target_bundle = bundle
                    break

            if not target_bundle:
                return None

            return self._render_bundle(target_bundle)

        except Exception:
            return None

    def _render_bundle(self, bundle: GarnishBundle) -> Path | None:
        """Render a single .garnish bundle to markdown."""
        # Load template content
        template_content = bundle.load_main_template()
        if not template_content:
            print(f"No template found for {bundle.name}")
            return None

        # Load component for schema
        component = self._load_component(bundle)
        if not component:
            print(f"Could not load component for {bundle.name}")
            return None

        # Create rendering context
        context = create_template_context(component, bundle)

        # Render template
        try:
            rendered_content = self.template_engine.render_template(
                template_content, context
            )
        except Exception as e:
            print(f"Template rendering failed for {bundle.name}: {e}")
            return None

        # Write output file
        output_file = self._get_output_path(bundle)
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(rendered_content, encoding="utf-8")
            return output_file
        except Exception as e:
            print(f"Failed to write output for {bundle.name}: {e}")
            return None

    def _load_component(self, bundle: GarnishBundle):
        """Load the actual Python component for schema extraction."""
        try:
            # Construct module path based on component type and name
            if bundle.component_type == "resource":
                module_path = f"pyvider.components.resources.{bundle.name}"
            elif bundle.component_type == "data_source":
                module_path = f"pyvider.components.data_sources.{bundle.name}"
            elif bundle.component_type == "function":
                # Functions might be in grouped modules
                module_path = f"pyvider.components.functions.{bundle.name}"
            else:
                return None

            try:
                module = importlib.import_module(module_path)

                # Look for component class or function
                # This is a simplified approach - real implementation would need
                # more sophisticated component discovery
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if hasattr(attr, "get_schema") or hasattr(
                        attr, "__pyvider_schema__"
                    ):
                        return attr

            except ImportError:
                # Try alternative module paths for functions
                if bundle.component_type == "function":
                    # Functions might be in grouped modules like numeric_functions
                    possible_modules = [
                        "pyvider.components.functions.numeric_functions",
                        "pyvider.components.functions.string_manipulation",
                        "pyvider.components.functions.collection_functions",
                        "pyvider.components.functions.type_conversion_functions",
                    ]

                    for mod_path in possible_modules:
                        try:
                            module = importlib.import_module(mod_path)
                            # Look for function with matching name
                            if hasattr(module, bundle.name):
                                return getattr(module, bundle.name)
                        except ImportError:
                            continue

            return None

        except Exception:
            return None

    def _get_output_path(self, bundle: GarnishBundle) -> Path:
        """Get output file path for a bundle."""
        # Create output directory structure
        if bundle.component_type == "resource":
            subdir = "resources"
        elif bundle.component_type == "data_source":
            subdir = "data-sources"
        elif bundle.component_type == "function":
            subdir = "functions"
        else:
            subdir = "components"

        return self.output_dir / subdir / f"{bundle.name}.md"


# 🍲🥄📄🪄

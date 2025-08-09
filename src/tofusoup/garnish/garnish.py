#
# tofusoup/garnish/garnish.py
#
"""Garnish bundle discovery and management."""

import importlib.util
from pathlib import Path

import attrs


@attrs.define
class GarnishBundle:
    """Represents a single .garnish bundle with its assets."""

    name: str
    garnish_dir: Path
    component_type: str  # "resource", "data_source", "function"

    @property
    def docs_dir(self) -> Path:
        """Directory containing documentation templates and partials."""
        return self.garnish_dir / "docs"

    @property
    def examples_dir(self) -> Path:
        """Directory containing example Terraform files."""
        return self.garnish_dir / "examples"

    @property
    def fixtures_dir(self) -> Path:
        """Directory containing fixture files for tests (inside examples dir)."""
        return self.examples_dir / "fixtures"

    def load_main_template(self) -> str | None:
        """Load the main template file for this component."""
        # Main template is typically <component_name>.tmpl.md
        template_file = self.docs_dir / f"{self.name}.tmpl.md"

        if not template_file.exists():
            return None

        try:
            return template_file.read_text(encoding="utf-8")
        except Exception:
            return None

    def load_examples(self) -> dict[str, str]:
        """Load all example files as a dictionary."""
        examples = {}

        if not self.examples_dir.exists():
            return examples

        for example_file in self.examples_dir.glob("*.tf"):
            try:
                examples[example_file.stem] = example_file.read_text(encoding="utf-8")
            except Exception:
                continue

        return examples

    def load_partials(self) -> dict[str, str]:
        """Load all partial files from docs directory (excluding main template)."""
        partials = {}

        if not self.docs_dir.exists():
            return partials

        # Load all files except the main template
        main_template_name = f"{self.name}.tmpl.md"

        for partial_file in self.docs_dir.glob("*"):
            if partial_file.is_file() and partial_file.name != main_template_name:
                try:
                    partials[partial_file.name] = partial_file.read_text(
                        encoding="utf-8"
                    )
                except Exception:
                    continue

        return partials

    def load_fixtures(self) -> dict[str, str]:
        """Load all fixture files from fixtures directory."""
        fixtures = {}

        if not self.fixtures_dir.exists():
            return fixtures

        for fixture_file in self.fixtures_dir.rglob("*"):
            if fixture_file.is_file():
                try:
                    # Use relative path from fixtures dir as key
                    rel_path = fixture_file.relative_to(self.fixtures_dir)
                    fixtures[str(rel_path)] = fixture_file.read_text(encoding="utf-8")
                except Exception:
                    continue

        return fixtures


class GarnishDiscovery:
    """Discovers .garnish bundles from installed packages."""

    def __init__(self, package_name: str = "pyvider.components"):
        self.package_name = package_name

    def discover_bundles(
        self, component_type: str | None = None
    ) -> list[GarnishBundle]:
        """Discover all .garnish bundles from the installed package."""
        bundles = []

        # Find the package location
        spec = importlib.util.find_spec(self.package_name)
        if not spec or not spec.origin:
            return bundles

        package_path = Path(spec.origin).parent

        # Search for .garnish directories
        for garnish_dir in package_path.rglob("*.garnish"):
            if not garnish_dir.is_dir():
                continue

            # Determine component type from path
            bundle_component_type = self._determine_component_type(garnish_dir)
            if component_type and bundle_component_type != component_type:
                continue

            # Check if this is a multi-component bundle
            sub_component_bundles = self._discover_sub_components(
                garnish_dir, bundle_component_type
            )
            if sub_component_bundles:
                # Multi-component bundle - use individual components
                bundles.extend(sub_component_bundles)
            else:
                # Single component bundle
                component_name = garnish_dir.name.replace(".garnish", "")

                bundle = GarnishBundle(
                    name=component_name,
                    garnish_dir=garnish_dir,
                    component_type=bundle_component_type,
                )

                bundles.append(bundle)

        return bundles

    def _discover_sub_components(
        self, garnish_dir: Path, component_type: str
    ) -> list[GarnishBundle]:
        """Discover individual components within a multi-component .garnish bundle."""
        sub_bundles = []

        # Look for subdirectories that contain docs/ and examples/ folders
        for item in garnish_dir.iterdir():
            if not item.is_dir():
                continue

            # Check if this looks like a component directory
            docs_dir = item / "docs"
            if docs_dir.exists() and docs_dir.is_dir():
                # This appears to be an individual component
                bundle = GarnishBundle(
                    name=item.name,  # Use the directory name as component name
                    garnish_dir=item,  # Point to the individual component directory
                    component_type=component_type,
                )
                sub_bundles.append(bundle)

        return sub_bundles

    def _determine_component_type(self, garnish_dir: Path) -> str:
        """Determine component type from the .garnish directory path."""
        path_parts = garnish_dir.parts

        if "resources" in path_parts:
            return "resource"
        elif "data_sources" in path_parts:
            return "data_source"
        elif "functions" in path_parts:
            return "function"
        else:
            # Default to resource if unclear
            return "resource"


# 🍲🥄📄🪄

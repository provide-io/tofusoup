#
# tofusoup/garnish/generator.py
#
"""Main documentation generator class and entry point."""

from pathlib import Path

from .garnish import GarnishDiscovery
from .models import FunctionInfo, ProviderInfo, ResourceInfo
from .schema import SchemaProcessor
from .templates import TemplateProcessor


class DocsGenerator:
    """Main documentation generator class."""

    def __init__(
        self,
        provider_dir: Path,
        provider_name: str | None = None,
        rendered_provider_name: str | None = None,
        examples_dir: str = "examples",
        templates_dir: str = "templates",
        output_dir: str = "docs",
        ignore_deprecated: bool = False,
    ):
        self.provider_dir = Path(provider_dir).resolve()
        self.examples_dir = self.provider_dir / examples_dir
        self.templates_dir = self.provider_dir / templates_dir
        self.output_dir = self.provider_dir / output_dir
        self.ignore_deprecated = ignore_deprecated

        # Determine provider name
        if provider_name:
            self.provider_name = provider_name
        else:
            # Extract from directory name, removing terraform-provider- prefix
            dir_name = self.provider_dir.name
            if dir_name.startswith("terraform-provider-"):
                self.provider_name = dir_name[19:]  # Remove "terraform-provider-"
            else:
                self.provider_name = dir_name

        self.rendered_provider_name = rendered_provider_name or self.provider_name

        # Internal state
        self.provider_schema = None
        self.provider_info: ProviderInfo | None = None
        self.resources: dict[str, ResourceInfo] = {}
        self.data_sources: dict[str, ResourceInfo] = {}
        self.functions: dict[str, FunctionInfo] = {}

        # Initialize processors
        self.schema_processor = SchemaProcessor(self)
        self.template_processor = TemplateProcessor(self)
        self.garnish_discovery = GarnishDiscovery()

    def process_examples(self):
        """Process example files and associate them with resources/data sources."""
        if not self.examples_dir.exists():
            return

        # Process provider examples
        provider_example = None
        if (self.examples_dir / "provider" / "provider.tf").exists():
            provider_example = (
                self.examples_dir / "provider" / "provider.tf"
            ).read_text()
        elif (self.examples_dir / "provider.tf").exists():
            provider_example = (self.examples_dir / "provider.tf").read_text()

        if provider_example and self.provider_info:
            self.provider_info.has_example = True
            self.provider_info.example_file = provider_example

        # Process resource examples
        for resource_name, resource_info in self.resources.items():
            example_patterns = [
                self.examples_dir / "resources" / f"{resource_name}" / "resource.tf",
                self.examples_dir / "resources" / f"{resource_name}.tf",
                self.examples_dir / f"{resource_name}.tf",
            ]

            for pattern in example_patterns:
                if pattern.exists():
                    resource_info.has_example = True
                    resource_info.example_file = pattern.read_text()
                    break

            # Process import examples
            import_patterns = [
                self.examples_dir / "resources" / f"{resource_name}" / "import.sh",
                self.examples_dir / "resources" / f"{resource_name}_import.sh",
                self.examples_dir / f"{resource_name}_import.sh",
            ]

            for pattern in import_patterns:
                if pattern.exists():
                    resource_info.has_import = True
                    resource_info.import_file = pattern.read_text()
                    break

        # Process data source examples
        for ds_name, ds_info in self.data_sources.items():
            example_patterns = [
                self.examples_dir / "data-sources" / f"{ds_name}" / "data-source.tf",
                self.examples_dir / "data-sources" / f"{ds_name}.tf",
                self.examples_dir / f"{ds_name}.tf",
            ]

            for pattern in example_patterns:
                if pattern.exists():
                    ds_info.has_example = True
                    ds_info.example_file = pattern.read_text()
                    break

        # Process function examples
        for func_name, func_info in self.functions.items():
            example_patterns = [
                self.examples_dir / "functions" / f"{func_name}" / "function.tf",
                self.examples_dir / "functions" / f"{func_name}.tf",
                self.examples_dir / f"{func_name}.tf",
            ]

            for pattern in example_patterns:
                if pattern.exists():
                    func_info.has_example = True
                    func_info.example_file = pattern.read_text()
                    break

    def generate(self):
        """Generate documentation for the provider."""
        print(f"🔍 Generating documentation for {self.provider_name} provider...")

        # Extract provider schema
        print("📋 Extracting provider schema...")
        self.provider_schema = self.schema_processor.extract_provider_schema()

        # Parse schema into our internal structures
        self.schema_processor.parse_provider_schema()

        # Process examples
        print("📁 Processing examples...")
        self.process_examples()

        # Generate missing templates
        print("📄 Generating missing templates...")
        self.template_processor.generate_missing_templates()

        # Render templates
        print("🎨 Rendering templates...")
        self.template_processor.render_templates()

        print(f"✅ Documentation generated successfully in {self.output_dir}")


def generate_docs(
    provider_dir: Path = Path(),
    provider_name: str | None = None,
    rendered_provider_name: str | None = None,
    examples_dir: str = "examples",
    templates_dir: str = "templates",
    output_dir: str = "docs",
    ignore_deprecated: bool = False,
) -> None:
    """Generate documentation for a Pyvider provider.

    Args:
        provider_dir: Path to the provider directory
        provider_name: Name of the provider (auto-detected if None)
        rendered_provider_name: Display name for the provider
        examples_dir: Directory containing example files
        templates_dir: Directory containing template files
        output_dir: Directory to output generated documentation
        ignore_deprecated: Whether to skip deprecated resources
    """
    generator = DocsGenerator(
        provider_dir=provider_dir,
        provider_name=provider_name,
        rendered_provider_name=rendered_provider_name,
        examples_dir=examples_dir,
        templates_dir=templates_dir,
        output_dir=output_dir,
        ignore_deprecated=ignore_deprecated,
    )

    generator.generate()


# 🍲🥄📄🪄

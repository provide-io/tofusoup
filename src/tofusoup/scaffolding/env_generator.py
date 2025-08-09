#
# tofusoup/scaffolding/env_generator.py
#
"""Generate env.sh and env.ps1 scripts from templates."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


class EnvScriptGenerator:
    """Generate environment setup scripts for both bash and PowerShell."""

    def __init__(self, template_base_dir: Path | None = None):
        """Initialize the generator with template directory."""
        if template_base_dir is None:
            template_base_dir = Path(__file__).parent / "templates" / "env"

        self.template_base_dir = template_base_dir

        # Create separate environments for sh and pwsh templates
        self.sh_env = Environment(
            loader=FileSystemLoader(template_base_dir / "sh"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        self.ps1_env = Environment(
            loader=FileSystemLoader(template_base_dir / "pwsh"),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate_env_script(
        self,
        project_name: str,
        output_path: Path,
        script_type: str = "sh",
        **kwargs: Any,
    ) -> None:
        """Generate an environment setup script.

        Args:
            project_name: Name of the project
            output_path: Path to write the script
            script_type: Either "sh" for bash or "ps1" for PowerShell
            **kwargs: Additional template variables
        """
        # Default configuration
        config = {
            "project_name": project_name,
            "env_profile_var": f"{project_name.upper()}_WORKENV_PROFILE",
            "venv_prefix": project_name.lower(),
            "use_spinner": script_type == "sh",  # PowerShell doesn't need spinner
            "strict_project_check": False,
            "install_siblings": True,
            "sibling_patterns": ["pyvider*"],
            "special_siblings": [
                {"name": "tofusoup", "var_name": "TOFUSOUP", "with_deps": True},
            ],
            "create_log_dir": True,
            "deduplicate_path": True,
            "include_tool_verification": False,
            "cleanup_logs": True,
            "useful_commands": [
                {
                    "command": f"{project_name.lower()} --help",
                    "description": f"{project_name} CLI",
                },
                {"command": "pytest", "description": "Run tests"},
                {"command": "deactivate", "description": "Exit environment"},
            ],
        }

        # Update with user-provided kwargs
        config.update(kwargs)

        # Select appropriate template and environment
        if script_type == "sh":
            template = self.sh_env.get_template("base.sh.j2")
        elif script_type == "ps1":
            template = self.ps1_env.get_template("base.ps1.j2")
        else:
            raise ValueError(f"Unknown script type: {script_type}")

        # Render and write
        content = template.render(**config)
        output_path.write_text(content)

        # Make executable if it's a shell script
        if script_type == "sh":
            output_path.chmod(output_path.stat().st_mode | 0o111)

    def generate_both_scripts(
        self,
        project_name: str,
        project_dir: Path,
        **kwargs: Any,
    ) -> tuple[Path, Path]:
        """Generate both env.sh and env.ps1 scripts.

        Returns:
            Tuple of (env.sh path, env.ps1 path)
        """
        sh_path = project_dir / "env.sh"
        ps1_path = project_dir / "env.ps1"

        self.generate_env_script(project_name, sh_path, "sh", **kwargs)
        self.generate_env_script(project_name, ps1_path, "ps1", **kwargs)

        return sh_path, ps1_path


def create_project_env_scripts(project_dir: Path) -> None:
    """Create environment scripts for a project based on its pyproject.toml."""
    pyproject_path = project_dir / "pyproject.toml"

    if not pyproject_path.exists():
        raise FileNotFoundError(f"No pyproject.toml found in {project_dir}")

    # Parse project name from pyproject.toml
    import tomllib

    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    project_name = pyproject.get("project", {}).get("name", project_dir.name)

    # Generate scripts
    generator = EnvScriptGenerator()
    sh_path, ps1_path = generator.generate_both_scripts(project_name, project_dir)

    print(f"✅ Generated {sh_path}")
    print(f"✅ Generated {ps1_path}")


# 🍲🥄📄🪄

#
# tofusoup/scaffolding/generator.py
#
"""Logic for scaffolding new provider projects and components."""

from pathlib import Path
import re

import jinja2

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _get_template_env() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(_TEMPLATE_DIR),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def scaffold_new_provider(project_dir: Path) -> Path:
    """Scaffolds a new Pyvider provider project structure."""
    if project_dir.exists() and any(project_dir.iterdir()):
        raise FileExistsError(f"Directory is not empty: {project_dir}")

    project_dir.mkdir(exist_ok=True)

    provider_name_match = re.search(r"terraform-provider-([\w-]+)", project_dir.name)
    if not provider_name_match:
        raise ValueError(
            "Project directory name must be in the format 'terraform-provider-<name>'"
        )
    provider_name = provider_name_match.group(1)

    src_root = project_dir / "src"
    provider_src_dir = src_root / provider_name
    provider_src_dir.mkdir(parents=True, exist_ok=True)

    env = _get_template_env()
    pyproject_template = env.get_template("pyproject.toml.j2")
    pyproject_content = pyproject_template.render(provider_name=provider_name)
    (project_dir / "pyproject.toml").write_text(pyproject_content)

    main_py_content = f'"""Main entry point for the {provider_name} provider."""\nfrom pyvider.provider_core import setup_provider\n\ndef serve():\n    setup_provider()\n'
    (provider_src_dir / "main.py").write_text(main_py_content)

    gitignore_content = "# Python\n__pycache__/\n*.py[cod]\n*$py.class\n*.egg-info/\n.env\n.venv\ndist/\nbuild/\n*.egg\n\n# Terraform\n.terraform/\n.terraform.lock.hcl\n*.tfstate\n*.tfstate.backup\ncrash.log\n"
    (project_dir / ".gitignore").write_text(gitignore_content)
    return project_dir


# 🍲🥄📄🪄

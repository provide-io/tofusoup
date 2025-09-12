"""
Configuration for CTY test suite.
Sets up environment variables from soup.toml configuration.
"""
import os
import pytest
from pathlib import Path
from tofusoup.common.config import load_tofusoup_config


@pytest.fixture(scope="session", autouse=True)
def setup_cty_test_environment():
    """
    Automatically set environment variables for the CTY test suite
    based on soup.toml configuration.
    """
    # Load the configuration
    project_root = Path(__file__).resolve()
    while project_root != project_root.parent:
        if (project_root / "pyproject.toml").exists():
            break
        project_root = project_root.parent
    
    config = load_tofusoup_config(project_root)
    
    # Get CTY test suite specific environment variables
    cty_env_vars = config.get("test_suite", {}).get("cty", {}).get("env_vars", {})
    
    # Set the environment variables for this test session
    for key, value in cty_env_vars.items():
        os.environ[key] = value
    
    yield
    
    # Optionally clean up (though pytest usually handles this)
    # for key in cty_env_vars:
    #     os.environ.pop(key, None)
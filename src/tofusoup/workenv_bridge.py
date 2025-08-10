#
# tofusoup/workenv_bridge.py
#
"""
Bridge module for integrating wrkenv with TofuSoup.

Provides backward compatibility for soup.toml and TOFUSOUP_WORKENV_ environment variables.
"""

from pathlib import Path
from typing import Optional

from wrkenv.env.config import WorkenvConfig, FileConfigSource, EnvironmentConfigSource


def create_soup_config(project_root: Optional[Path] = None) -> WorkenvConfig:
    """
    Create a WorkenvConfig that maintains TofuSoup backward compatibility.
    
    This function creates a configuration that:
    1. Supports legacy TOFUSOUP_WORKENV_ environment variables
    2. Reads from soup.toml files
    3. Falls back to wrkenv.toml if available
    
    Args:
        project_root: Optional project root directory. If not provided, uses current directory.
        
    Returns:
        WorkenvConfig configured for TofuSoup compatibility
    """
    if project_root is None:
        project_root = Path.cwd()
    
    sources = []
    
    # Priority 1: Support legacy TOFUSOUP_WORKENV_ environment variables
    sources.append(EnvironmentConfigSource("TOFUSOUP_WORKENV"))
    
    # Priority 2: Standard WRKENV_ environment variables
    sources.append(EnvironmentConfigSource("WRKENV"))
    
    # Priority 3: Look for soup.toml in project root
    soup_toml = project_root / "soup.toml"
    if soup_toml.exists():
        sources.append(FileConfigSource(soup_toml, "workenv"))
    
    # Priority 4: Look for soup.toml in soup/ subdirectory (common pattern)
    soup_subdir_toml = project_root / "soup" / "soup.toml"
    if soup_subdir_toml.exists():
        sources.append(FileConfigSource(soup_subdir_toml, "workenv"))
    
    # Priority 5: Check for wrkenv.toml as fallback
    wrkenv_toml = project_root / "wrkenv.toml"
    if wrkenv_toml.exists():
        sources.append(FileConfigSource(wrkenv_toml, "workenv"))
    
    return WorkenvConfig(sources)


def get_terraform_flavor_from_soup(project_root: Optional[Path] = None) -> str:
    """
    Get the configured terraform flavor from soup.toml.
    
    Args:
        project_root: Optional project root directory
        
    Returns:
        "opentofu" or "terraform" based on configuration
    """
    config = create_soup_config(project_root)
    return config.get_setting("terraform_flavor", "terraform")


def ensure_workenv_tools(config: Optional[WorkenvConfig] = None) -> None:
    """
    Ensure all configured workenv tools are installed.
    
    This is useful for soup commands that depend on having tools available.
    
    Args:
        config: Optional WorkenvConfig. If not provided, creates one with soup compatibility.
    """
    from wrkenv import get_tool_manager
    
    if config is None:
        config = create_soup_config()
    
    tools = config.get_all_tools()
    for tool_name, version in tools.items():
        if version:
            manager = get_tool_manager(tool_name, config)
            if manager:
                current = manager.get_installed_version()
                if current != version:
                    print(f"Installing {tool_name} {version}...")
                    manager.install_version(version)


# 🍲🧰🌍🪄
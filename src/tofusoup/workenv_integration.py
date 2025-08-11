"""
Integration between TofuSoup and wrkenv.

This module provides functionality to inject TofuSoup's workenv configuration
from soup.toml into wrkenv, making wrkenv.toml optional for TofuSoup users.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import toml

from wrkenv import WorkenvConfig


def load_soup_config(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load the soup.toml configuration file.
    
    Args:
        project_root: Optional project root directory. If not provided, uses current directory.
        
    Returns:
        Dictionary containing the soup configuration, or empty dict if not found.
    """
    if project_root is None:
        project_root = Path.cwd()
    
    soup_toml_path = project_root / "soup.toml"
    
    if soup_toml_path.exists():
        with open(soup_toml_path, 'r') as f:
            return toml.load(f)
    
    return {}


def create_workenv_config_with_soup(project_root: Optional[Path] = None) -> WorkenvConfig:
    """
    Create a WorkenvConfig instance that includes configuration from soup.toml.
    
    This allows TofuSoup to inject its workenv configuration into wrkenv,
    making wrkenv.toml optional for TofuSoup users.
    
    Args:
        project_root: Optional project root directory.
        
    Returns:
        WorkenvConfig instance with soup.toml configuration injected.
    """
    # Load soup.toml
    soup_config = load_soup_config(project_root)
    workenv_section = soup_config.get('workenv', {})
    
    if not workenv_section:
        # No workenv config in soup.toml, just return standard WorkenvConfig
        return WorkenvConfig(project_root=project_root)
    
    # Create a custom ConfigSource for soup.toml
    from wrkenv.env.config import FileConfigSource
    
    # Create a soup.toml source
    soup_source = FileConfigSource(project_root / "soup.toml" if project_root else Path.cwd() / "soup.toml", "workenv")
    
    # Create WorkenvConfig and add soup source with highest priority
    config = WorkenvConfig(project_root=project_root)
    config.sources.insert(0, soup_source)  # Insert at beginning for highest priority
    
    return config


def get_matrix_config_from_soup(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get matrix configuration from soup.toml.
    
    Args:
        project_root: Optional project root directory.
        
    Returns:
        Matrix configuration dictionary.
    """
    soup_config = load_soup_config(project_root)
    return soup_config.get('workenv', {}).get('matrix', {})
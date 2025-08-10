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
    
    # Create a temporary config dict to inject
    config_overrides = {}
    
    # Map soup.toml workenv settings to WorkenvConfig format
    if 'terraform_flavor' in workenv_section:
        config_overrides['terraform_flavor'] = workenv_section['terraform_flavor']
    
    if 'tools' in workenv_section:
        config_overrides['tools'] = workenv_section['tools']
    
    if 'settings' in workenv_section:
        settings = workenv_section['settings']
        if 'verify_checksums' in settings:
            config_overrides['verify_checksums'] = settings['verify_checksums']
        if 'cache_downloads' in settings:
            config_overrides['cache_downloads'] = settings['cache_downloads']
    
    # Handle matrix configuration
    if 'matrix' in workenv_section:
        config_overrides['matrix'] = workenv_section['matrix']
    
    # Create WorkenvConfig with overrides
    # Note: WorkenvConfig will still read wrkenv.toml if it exists,
    # but soup.toml values will take precedence
    config = WorkenvConfig(project_root=project_root)
    
    # Apply overrides
    for key, value in config_overrides.items():
        config._config[key] = value
    
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
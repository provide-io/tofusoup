"""
Test the wrkenv integration and backward compatibility.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from tofusoup.workenv_bridge import create_soup_config, get_terraform_flavor_from_soup


class TestWorkenvBridge:
    """Test the workenv bridge functionality."""
    
    def test_create_soup_config_reads_soup_toml(self, tmp_path):
        """Test that create_soup_config properly reads soup.toml."""
        # Create a soup.toml file
        soup_toml = tmp_path / "soup.toml"
        soup_toml.write_text("""
[workenv]
terraform_flavor = "opentofu"

[workenv.tools]
terraform = "1.5.7"
tofu = "1.6.2"
go = "1.21.5"
""")
        
        # Create config
        config = create_soup_config(tmp_path)
        
        # Verify it reads the values
        assert config.get_setting("terraform_flavor") == "opentofu"
        tools = config.get_all_tools()
        assert tools.get("terraform") == "1.5.7"
        assert tools.get("tofu") == "1.6.2"
        assert tools.get("go") == "1.21.5"
    
    def test_create_soup_config_fallback_to_wrkenv_toml(self, tmp_path):
        """Test fallback to wrkenv.toml when soup.toml doesn't exist."""
        # Create only wrkenv.toml
        wrkenv_toml = tmp_path / "wrkenv.toml"
        wrkenv_toml.write_text("""
[workenv.tools]
terraform = "1.6.0"
""")
        
        config = create_soup_config(tmp_path)
        tools = config.get_all_tools()
        assert tools.get("terraform") == "1.6.0"
    
    def test_legacy_environment_variables(self):
        """Test that legacy TOFUSOUP_WORKENV_ variables are supported."""
        with patch.dict(os.environ, {
            "TOFUSOUP_WORKENV_TERRAFORM_VERSION": "1.5.5",
            "TOFUSOUP_WORKENV_VERIFY_CHECKSUMS": "false",
        }):
            config = create_soup_config()
            
            # Should read from legacy env vars
            assert config.get_tool_version("terraform") == "1.5.5"
            assert config.get_setting("verify_checksums") == False
    
    def test_get_terraform_flavor_from_soup(self, tmp_path):
        """Test getting terraform flavor from soup.toml."""
        soup_toml = tmp_path / "soup.toml"
        soup_toml.write_text("""
[workenv]
terraform_flavor = "opentofu"
""")
        
        flavor = get_terraform_flavor_from_soup(tmp_path)
        assert flavor == "opentofu"
    
    def test_get_terraform_flavor_default(self, tmp_path):
        """Test default terraform flavor when not configured."""
        flavor = get_terraform_flavor_from_soup(tmp_path)
        assert flavor == "terraform"  # Default


class TestMatrixIntegration:
    """Test the matrix testing integration."""
    
    @pytest.mark.asyncio
    async def test_matrix_generation(self):
        """Test that matrix combinations are generated correctly."""
        from tofusoup.testing.matrix import VersionMatrix
        
        # Create a mock config with matrix settings
        mock_config = MagicMock()
        mock_config.get_setting.return_value = {
            "versions": {
                "terraform": ["1.5.7", "1.6.0"],
                "tofu": ["1.6.2", "1.7.0"],
            }
        }
        
        # Create matrix with base tools
        base_tools = {"terraform": "1.5.0", "tofu": "1.6.0"}
        matrix = VersionMatrix(base_tools, mock_config)
        
        # Generate combinations
        combinations = matrix.generate_combinations()
        
        # Should have base versions plus matrix versions
        # Base: terraform 1.5.0, tofu 1.6.0
        # Matrix adds: terraform [1.5.7, 1.6.0], tofu [1.6.2, 1.7.0]
        # Total unique: terraform [1.5.0, 1.5.7, 1.6.0] x tofu [1.6.0, 1.6.2, 1.7.0]
        assert len(combinations) > 0
        
        # Check that all tools are present in each combination
        for combo in combinations:
            assert "terraform" in combo.tools
            assert "tofu" in combo.tools


class TestCLIIntegration:
    """Test CLI integration."""
    
    def test_workenv_command_available(self):
        """Test that workenv commands are available in TofuSoup CLI."""
        # This is already configured in cli.py
        from tofusoup.cli import LAZY_SUBCOMMANDS
        
        assert "workenv" in LAZY_SUBCOMMANDS
        assert LAZY_SUBCOMMANDS["workenv"] == ("wrkenv.env.cli", "workenv_cli")
        
        # Also check the alias
        assert "we" in LAZY_SUBCOMMANDS
        assert LAZY_SUBCOMMANDS["we"] == ("wrkenv.env.cli", "workenv_cli")


# Test helper to verify no tofusoup imports in wrkenv
def test_no_tofusoup_imports_in_wrkenv():
    """Verify wrkenv doesn't import tofusoup (clean separation)."""
    import subprocess
    import sys
    
    # Try to import wrkenv and check its dependencies
    result = subprocess.run(
        [sys.executable, "-c", "import wrkenv; print('OK')"],
        capture_output=True,
        text=True
    )
    
    # Should succeed without tofusoup
    assert result.returncode == 0
    assert "OK" in result.stdout
    
    # Check that tofusoup is not in wrkenv's imports
    result = subprocess.run(
        [sys.executable, "-c", 
         "import wrkenv; import sys; print('tofusoup' not in sys.modules)"],
        capture_output=True,
        text=True
    )
    assert "True" in result.stdout
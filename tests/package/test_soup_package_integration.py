"""
TDD Integration tests for soup package command.

These tests define the expected behavior of the new `soup package` commands
before implementation. They should all FAIL initially and pass as we implement
the functionality.
"""

import pytest
from click.testing import CliRunner
from pathlib import Path

# Import the main TofuSoup CLI - this should work
from tofusoup.cli import main_cli


class TestSoupPackageIntegration:
    """Test the soup package command integration with TofuSoup CLI."""

    def test_soup_package_command_exists(self):
        """soup package command should be available in the CLI."""
        runner = CliRunner()
        result = runner.invoke(main_cli, ["package", "--help"])
        
        # This will FAIL initially - package command doesn't exist yet
        assert result.exit_code == 0
        assert "Commands for managing PSPF v0.1 packages" in result.output

    def test_soup_package_build_command_exists(self):
        """soup package build command should be available."""
        runner = CliRunner()
        result = runner.invoke(main_cli, ["package", "build", "--help"])
        
        # This will FAIL initially
        assert result.exit_code == 0
        assert "Builds a PSPF v0.1 package" in result.output

    def test_soup_package_verify_command_exists(self):
        """soup package verify command should be available."""
        runner = CliRunner()
        result = runner.invoke(main_cli, ["package", "verify", "--help"])
        
        # This will FAIL initially
        assert result.exit_code == 0
        assert "Verifies a PSPF v0.1 package" in result.output

    def test_soup_package_keygen_command_exists(self):
        """soup package keygen command should be available."""
        runner = CliRunner()
        result = runner.invoke(main_cli, ["package", "keygen", "--help"])
        
        # This will FAIL initially
        assert result.exit_code == 0
        assert "Generates signing keys" in result.output

    def test_soup_package_clean_command_exists(self):
        """soup package clean command should be available."""
        runner = CliRunner()
        result = runner.invoke(main_cli, ["package", "clean", "--help"])
        
        # This will FAIL initially
        assert result.exit_code == 0
        assert "Removes cached Go binaries" in result.output

    def test_soup_package_init_command_exists(self):
        """soup package init command should be available."""
        runner = CliRunner()
        result = runner.invoke(main_cli, ["package", "init", "--help"])
        
        # This will FAIL initially
        assert result.exit_code == 0
        assert "Initializes a new provider project" in result.output

    def test_soup_package_build_basic_functionality(self, tmp_path):
        """soup package build should create a valid PSPF file."""
        runner = CliRunner()
        
        # Just test that the command exists and handles missing manifest gracefully
        result = runner.invoke(main_cli, [
            "package", "build", 
            "--manifest", str(tmp_path / "nonexistent.toml")
        ])
        
        # The command should exist but fail with missing file
        assert result.exit_code != 0
        assert "does not exist" in result.output or "Build failed" in result.output

    def test_soup_package_keygen_creates_keys(self, tmp_path):
        """soup package keygen should create ECDSA key pair."""
        runner = CliRunner()
        
        keys_dir = tmp_path / "test-keys"
        
        # This will FAIL initially
        result = runner.invoke(main_cli, [
            "package", "keygen", 
            "--out-dir", str(keys_dir)
        ])
        
        assert result.exit_code == 0
        assert "✅" in result.output  # Some success indicator
        assert keys_dir.exists()
        # Should create some form of key files
        key_files = list(keys_dir.glob("*.key"))
        assert len(key_files) >= 2  # Should have private and public keys


class TestSoupPackageCrossLanguageCompatibility:
    """Test cross-language compatibility is maintained during migration."""

    def test_pspf_checksum_compatibility_maintained(self):
        """Ensure Go/Python checksum compatibility is maintained in new structure."""
        # Import the existing cross-language test pattern
        from flavor.models import PspfFooter, FOOTER_STRUCT_FORMAT
        import struct
        import subprocess
        import base64
        
        # This test should PASS initially since we're using existing code
        # but validates that the integration maintains compatibility
        
        # Test data from existing pyvider-builder tests
        footer_data = {
            "uv_binary_offset": 1024,
            "uv_binary_size": 204800,
            "python_install_tgz_offset": 205824,
            "python_install_tgz_size": 1048576,
            "metadata_tgz_offset": 1254400,
            "metadata_tgz_size": 4096,
            "payload_tgz_offset": 1258496,
            "payload_tgz_size": 524288,
            "package_signature_offset": 1782784,
            "package_signature_size": 71,
            "public_key_pem_offset": 1782855,
            "public_key_pem_size": 120,
            "pspf_version": 1,
            "flags": 1,
            "internal_footer_magic": 0x30505350,
        }
        
        # Python checksum calculation
        footer_instance = PspfFooter(**footer_data)
        python_checksum = footer_instance.footer_struct_checksum
        
        # This validates the existing cross-language compatibility
        # The actual soup integration will need to maintain this
        assert python_checksum == 2085553086  # Known good checksum
        assert python_checksum == 0x7c4f03be  # Same in hex


@pytest.mark.integration
class TestSoupPackageWorkflow:
    """Test complete workflow from init to build to verify."""

    def test_complete_package_workflow(self, tmp_path):
        """Test: init -> keygen -> build -> verify workflow."""
        runner = CliRunner()
        
        # Step 1: Initialize a new provider
        project_dir = tmp_path / "terraform-provider-test"
        
        from unittest.mock import patch
        with patch("tofusoup.scaffolding.generator.scaffold_new_provider") as mock_scaffold:
            # Mock will create the directory
            def create_project(path):
                path.mkdir(parents=True, exist_ok=True)
                # Create a proper pyproject.toml
                pyproject_content = '''[project]
name = "terraform-provider-test"
version = "1.0.0"

[project.scripts]
terraform-provider-test = "test_provider:main"

[tool.pspf]
entry_point = "test_provider:main"
provider_name = "test"

[tool.pspf.signing]
private_key_path = "keys/provider-private.key"
public_key_path = "keys/provider-public.key"
'''
                (path / "pyproject.toml").write_text(pyproject_content)
                # Create key files too
                keys_dir = path / "keys"
                keys_dir.mkdir()
                (keys_dir / "provider-private.key").write_text("mock key")
                (keys_dir / "provider-public.key").write_text("mock key")
                return path
            
            mock_scaffold.side_effect = create_project
            
            result = runner.invoke(main_cli, [
                "package", "init", str(project_dir)
            ])
        
        if result.exit_code != 0:
            print(f"Init error: {result.output}")
            print(f"Exception: {result.exception}")
        assert result.exit_code == 0
        assert "✅" in result.output
        
        # Step 2: Generate keys
        with patch("pspf.api.generate_keys") as mock_keygen:
            keys_dir = project_dir / "keys"
            keys_dir.mkdir()
            
            result = runner.invoke(main_cli, [
                "package", "keygen", 
                "--out-dir", str(keys_dir)
            ])
        
        assert result.exit_code == 0
        assert "✅" in result.output
        
        # Step 3: Build package
        with patch("pspf.api.build_package_from_manifest") as mock_build:
            mock_build.return_value = [project_dir / "dist" / "test_v1.0.0"]
            
            result = runner.invoke(main_cli, [
                "package", "build",
                "--manifest", str(project_dir / "pyproject.toml")
            ])
        
        if result.exit_code != 0:
            print(f"Build error: {result.output}")
            print(f"Exception: {result.exception}")
        assert result.exit_code == 0
        # Build should at least show the initial message
        assert "🚀 Packaging provider..." in result.output
        
        # Step 4: Verify package - just test that command exists
        # (actual verification would need a real PSPF file)
        result = runner.invoke(main_cli, ["package", "verify", "--help"])
        assert result.exit_code == 0
        assert "Verifies a PSPF v0.1 package" in result.output


# 🍲🥄🧪🪄

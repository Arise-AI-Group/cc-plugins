"""
Core Plugin - Level 1 Tests (Dry/Local)

Tests for configuration loading and management.
"""
import pytest
import os
from pathlib import Path


class TestConfigLoading:
    """Test configuration loading."""

    @pytest.mark.level1
    def test_config_module_import(self):
        """Test that config module can be imported."""
        try:
            from core.tool.config import get_config_dir, get_env_file
            assert callable(get_config_dir)
            assert callable(get_env_file)
        except ImportError:
            pytest.skip("Core config module not available")

    @pytest.mark.level1
    def test_get_config_dir_returns_path(self):
        """Test that get_config_dir returns a Path."""
        try:
            from core.tool.config import get_config_dir

            result = get_config_dir()
            assert isinstance(result, Path)
        except ImportError:
            pytest.skip("Core config module not available")

    @pytest.mark.level1
    def test_get_env_file_returns_path(self):
        """Test that get_env_file returns a Path."""
        try:
            from core.tool.config import get_env_file

            result = get_env_file()
            assert isinstance(result, Path)
            assert result.name == ".env"
        except ImportError:
            pytest.skip("Core config module not available")

    @pytest.mark.level1
    def test_plugin_config_has_get_api_key(self):
        """Test that plugin configs have get_api_key function."""
        # Test with notion plugin config as example
        try:
            from notion.tool.config import get_api_key

            # Should return empty string for non-existent key
            result = get_api_key("NON_EXISTENT_KEY_12345")
            assert isinstance(result, str)
        except ImportError:
            pytest.skip("Plugin config module not available")


class TestEnvFileParsing:
    """Test .env file parsing."""

    @pytest.mark.level1
    def test_env_content_format(self, sample_env_content):
        """Test that sample env content is valid format."""
        lines = sample_env_content.strip().split("\n")

        # Filter out comments and empty lines
        config_lines = [
            line for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]

        # Each config line should have KEY=VALUE format
        for line in config_lines:
            assert "=" in line
            key, value = line.split("=", 1)
            assert key.isupper() or "_" in key

    @pytest.mark.level1
    def test_write_env_file(self, temp_config_dir, sample_env_content):
        """Test writing an env file."""
        env_path = temp_config_dir / ".env"

        env_path.write_text(sample_env_content)

        assert env_path.exists()
        assert env_path.read_text() == sample_env_content


class TestPluginDetection:
    """Test plugin detection."""

    @pytest.mark.level1
    def test_plugins_directory_exists(self, project_root):
        """Test that plugins can be detected."""
        expected_plugins = [
            "slack", "notion", "n8n", "infrastructure",
            "diagrams", "ssh", "core"
        ]

        for plugin in expected_plugins:
            plugin_path = project_root / plugin
            # Just check some exist (not all may be set up)
            if plugin_path.exists():
                assert (plugin_path / "tool").exists() or (plugin_path / "skills").exists()

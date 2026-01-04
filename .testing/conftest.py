"""
Root conftest.py - ensures project root is in Python path.

This file is loaded by pytest before any other conftest files,
ensuring that imports like 'from .testing.helpers' work correctly.
"""
import os
import sys
import json
import pytest
from pathlib import Path
from dotenv import load_dotenv

# .testing/ is one level below project root
TESTING_ROOT = Path(__file__).parent
PROJECT_ROOT = TESTING_ROOT.parent

# Ensure project root is in path for plugin imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure .testing root is in path for helpers imports
if str(TESTING_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTING_ROOT))

# Load credentials
ENV_PATH = Path.home() / ".config" / "cc-plugins" / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Test configuration
TEST_PREFIX = "test-ccplugins-"


@pytest.fixture(scope="session")
def test_prefix():
    """Standard prefix for all test-created resources."""
    return TEST_PREFIX


@pytest.fixture(scope="session")
def project_root():
    """Project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def mock_responses_path():
    """Path to mock response fixtures."""
    return TESTING_ROOT / "fixtures" / "responses"


@pytest.fixture(scope="session")
def load_mock_response(mock_responses_path):
    """Factory fixture to load mock responses from JSON files."""
    def _load(service: str, operation: str):
        file_path = mock_responses_path / service / f"{operation}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Mock response not found: {file_path}")
        with open(file_path) as f:
            return json.load(f)
    return _load


# Credential check fixtures
@pytest.fixture(scope="session")
def has_slack_credentials():
    return bool(os.getenv("SLACK_BOT_TOKEN"))


@pytest.fixture(scope="session")
def has_notion_credentials():
    return bool(os.getenv("NOTION_API_KEY"))


@pytest.fixture(scope="session")
def has_n8n_credentials():
    return bool(os.getenv("N8N_API_URL") and os.getenv("N8N_API_KEY"))


@pytest.fixture(scope="session")
def has_cloudflare_credentials():
    return bool(os.getenv("CLOUDFLARE_API_TOKEN"))


@pytest.fixture(scope="session")
def has_dokploy_credentials():
    return bool(os.getenv("DOKPLOY_URL") and os.getenv("DOKPLOY_API_KEY"))


@pytest.fixture(scope="session")
def has_ssh_credentials():
    return bool(os.getenv("SSH_KEY_PATH") or os.getenv("SSH_PASSWORD"))


# Cleanup registry
class CleanupRegistry:
    """Registry for tracking resources that need cleanup after tests."""

    def __init__(self):
        self._resources = {}

    def register(self, resource_type: str, resource_info: dict):
        if resource_type not in self._resources:
            self._resources[resource_type] = []
        self._resources[resource_type].append(resource_info)

    def get_resources(self, resource_type: str):
        return self._resources.get(resource_type, [])

    def clear(self, resource_type: str = None):
        if resource_type:
            self._resources[resource_type] = []
        else:
            self._resources = {}


@pytest.fixture(scope="function")
def cleanup_registry():
    """Per-test cleanup registry."""
    return CleanupRegistry()


# Custom CLI options
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--test-level",
        action="store",
        default="3",
        help="Maximum test level to run: 1 (dry), 2 (read-only), 3 (write)"
    )

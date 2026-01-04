"""
Core plugin test fixtures.

Note: Core plugin is primarily for configuration management,
so tests focus on config loading and validation.
"""
import os
import sys
import pytest
from pathlib import Path
import tempfile

# .testing/plugins/core/conftest.py -> project root is 4 levels up
TESTING_ROOT = Path(__file__).parent.parent.parent  # .testing/
PROJECT_ROOT = TESTING_ROOT.parent  # cc-plugins/

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TESTING_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTING_ROOT))


@pytest.fixture
def temp_config_dir():
    """Temporary config directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_env_content():
    """Sample .env file content for testing."""
    return """
# Test environment file
SLACK_BOT_TOKEN=xoxb-test-token
NOTION_API_KEY=secret_test_key
N8N_API_URL=https://n8n.example.com
N8N_API_KEY=test_api_key
"""

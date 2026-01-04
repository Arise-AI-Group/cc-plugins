"""
n8n plugin test fixtures.
"""
import os
import sys
import pytest
from pathlib import Path

# .testing/plugins/n8n/conftest.py -> project root is 4 levels up
TESTING_ROOT = Path(__file__).parent.parent.parent  # .testing/
PROJECT_ROOT = TESTING_ROOT.parent  # cc-plugins/

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TESTING_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTING_ROOT))

from helpers.mock_factory import MockClientFactory
from helpers.cleanup import cleanup_n8n_resources


@pytest.fixture
def mock_n8n_client():
    """Fully mocked n8n client for Level 1 tests."""
    factory = MockClientFactory()
    return factory.create_n8n_client()


@pytest.fixture(scope="module")
def n8n_client(has_n8n_credentials):
    """Real n8n client for Level 2 and 3 tests."""
    if not has_n8n_credentials:
        pytest.skip("n8n credentials not configured")

    try:
        from n8n.tool.n8n_api import N8nClient
    except ImportError:
        pytest.skip("n8n client not available")

    return N8nClient()


@pytest.fixture
def n8n_cleanup(n8n_client, cleanup_registry):
    """Cleanup fixture for n8n resources."""
    yield cleanup_registry
    cleanup_n8n_resources(n8n_client, cleanup_registry)


@pytest.fixture
def find_existing_workflow(n8n_client):
    """Helper to find an existing workflow for read-only tests."""
    def _find():
        workflows = n8n_client.list_workflows()
        return workflows[0] if workflows else None
    return _find

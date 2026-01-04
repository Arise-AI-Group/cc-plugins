"""
Notion plugin test fixtures.
"""
import os
import sys
import pytest
from pathlib import Path

# .testing/plugins/notion/conftest.py -> project root is 4 levels up
TESTING_ROOT = Path(__file__).parent.parent.parent  # .testing/
PROJECT_ROOT = TESTING_ROOT.parent  # cc-plugins/

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TESTING_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTING_ROOT))

from helpers.mock_factory import MockClientFactory
from helpers.cleanup import cleanup_notion_resources


@pytest.fixture
def mock_notion_client():
    """Fully mocked Notion client for Level 1 tests."""
    factory = MockClientFactory()
    return factory.create_notion_client()


@pytest.fixture(scope="module")
def notion_client(has_notion_credentials):
    """Real Notion client for Level 2 and 3 tests."""
    if not has_notion_credentials:
        pytest.skip("Notion credentials not configured")

    try:
        from notion.tool.notion_api import NotionClient
    except ImportError:
        pytest.skip("Notion client not available")

    return NotionClient()


@pytest.fixture
def notion_cleanup(notion_client, cleanup_registry):
    """Cleanup fixture for Notion resources."""
    yield cleanup_registry
    cleanup_notion_resources(notion_client, cleanup_registry)


@pytest.fixture
def find_existing_page(notion_client):
    """Helper to find an existing page for read-only tests."""
    def _find():
        # search() returns List[Dict] directly
        results = notion_client.search(query="", page_size=10)
        pages = [r for r in results if r.get("object") == "page"]
        return pages[0] if pages else None
    return _find


@pytest.fixture
def find_existing_database(notion_client):
    """Helper to find an existing database for read-only tests."""
    def _find():
        # search() uses filter_type param, returns data_source objects
        results = notion_client.search(query="", filter_type="database", page_size=10)
        # Notion API returns "data_source" for databases, not "database"
        dbs = [r for r in results if r.get("object") in ("database", "data_source")]
        return dbs[0] if dbs else None
    return _find

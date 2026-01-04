"""
Notion Plugin - Level 2 Tests (Read-Only)
"""
import pytest


@pytest.mark.level2
@pytest.mark.requires_credentials
class TestNotionReadOperations:
    """Read-only tests against real Notion API."""

    def test_search_workspace(self, notion_client):
        """Test searching the workspace."""
        # search() returns List[Dict] directly, not a wrapped dict
        results = notion_client.search(query="", page_size=5)

        assert isinstance(results, list)

    def test_get_page(self, notion_client, find_existing_page):
        """Test getting a page."""
        page = find_existing_page()
        if not page:
            pytest.skip("No pages available for testing")

        result = notion_client.get_page(page["id"])

        assert result["id"] == page["id"]
        assert result["object"] == "page"

    def test_query_database(self, notion_client, find_existing_database):
        """Test querying a database."""
        db = find_existing_database()
        if not db:
            pytest.skip("No databases available for testing")

        # query_database returns dict with "results" key
        results = notion_client.query_database(db["id"], page_size=5)

        assert isinstance(results, dict)
        assert "results" in results

    def test_list_users(self, notion_client):
        """Test listing users."""
        users = notion_client.list_users()

        assert isinstance(users, list)

    def test_get_bot_user(self, notion_client):
        """Test getting bot user (integration)."""
        # Method is get_bot_user(), not get_current_user()
        user = notion_client.get_bot_user()

        assert isinstance(user, dict)
        assert "id" in user

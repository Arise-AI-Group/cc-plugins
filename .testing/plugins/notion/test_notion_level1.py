"""
Notion Plugin - Level 1 Tests (Dry/Mocked)
"""
import pytest


class TestNotionMockedOperations:
    """Test operations with mocked responses."""

    @pytest.mark.level1
    def test_get_page_returns_dict(self, mock_notion_client):
        """Test that get_page returns page details."""
        page = mock_notion_client.get_page("page-001")

        assert isinstance(page, dict)
        assert "id" in page
        assert page.get("object") == "page"

    @pytest.mark.level1
    def test_query_database_returns_results(self, mock_notion_client):
        """Test that query_database returns results."""
        result = mock_notion_client.query_database("db-001")

        assert isinstance(result, dict)
        assert "results" in result
        assert isinstance(result["results"], list)

    @pytest.mark.level1
    def test_search_returns_list(self, mock_notion_client):
        """Test that search returns a list of results."""
        # search() returns List[Dict] directly, not a dict with "results" key
        result = mock_notion_client.search("test")

        assert isinstance(result, list)

    @pytest.mark.level1
    def test_list_users_returns_list(self, mock_notion_client):
        """Test that list_users returns a list."""
        users = mock_notion_client.list_users()

        assert isinstance(users, list)

    @pytest.mark.level1
    def test_create_page_returns_page(self, mock_notion_client):
        """Test that create_page returns page details."""
        page = mock_notion_client.create_page({})

        assert isinstance(page, dict)
        assert "id" in page

    @pytest.mark.level1
    def test_archive_page_returns_page(self, mock_notion_client):
        """Test that archive_page returns the archived page."""
        # archive_page returns the updated page dict with archived=True
        result = mock_notion_client.archive_page("page-001")

        assert isinstance(result, dict)
        assert result.get("archived") is True


class TestNotionResponseParsing:
    """Test response parsing."""

    @pytest.mark.level1
    def test_page_response_structure(self, load_mock_response):
        """Test page response structure from fixtures."""
        page = load_mock_response("notion", "get_page")

        assert isinstance(page, dict)
        assert "id" in page
        assert "object" in page
        assert page["object"] == "page"

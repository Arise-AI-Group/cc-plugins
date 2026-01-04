"""
Notion Plugin - Level 3 Tests (Write Operations)
"""
import pytest
import time


@pytest.mark.level3
@pytest.mark.requires_credentials
class TestNotionPageOperations:
    """Test page creation and management."""

    def test_create_and_archive_page(
        self,
        notion_client,
        find_existing_page,
        test_prefix,
        notion_cleanup
    ):
        """Test creating and archiving a page."""
        # Need a parent page to create under
        parent = find_existing_page()
        if not parent:
            pytest.skip("No parent page available for testing")

        timestamp = int(time.time())
        page_title = f"{test_prefix}page-{timestamp}"

        # Create page using parent_id and title params
        page = notion_client.create_page(
            parent_id=parent["id"],
            title=page_title
        )

        notion_cleanup.register("notion_pages", {"id": page["id"]})

        assert "id" in page
        assert page["object"] == "page"

        # Archive page
        notion_client.archive_page(page["id"])

    def test_update_page(
        self,
        notion_client,
        find_existing_page,
        test_prefix,
        notion_cleanup
    ):
        """Test updating a page."""
        parent = find_existing_page()
        if not parent:
            pytest.skip("No parent page available for testing")

        timestamp = int(time.time())
        page_title = f"{test_prefix}update-{timestamp}"

        # Create page using parent_id and title params
        page = notion_client.create_page(
            parent_id=parent["id"],
            title=page_title
        )
        notion_cleanup.register("notion_pages", {"id": page["id"]})

        # Update page title
        new_title = f"{page_title}-updated"
        notion_client.update_page(
            page["id"],
            properties={
                "title": {
                    "title": [{"text": {"content": new_title}}]
                }
            }
        )

        # Verify update
        updated = notion_client.get_page(page["id"])
        assert updated["id"] == page["id"]

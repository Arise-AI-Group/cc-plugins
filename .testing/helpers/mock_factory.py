"""
Mock client factories for Level 1 (dry) tests.

Provides pre-configured mock objects that simulate API responses
without making any network calls.
"""
from unittest.mock import MagicMock
from typing import Dict, Any, Optional, List
import json
from pathlib import Path


class MockClientFactory:
    """Factory for creating pre-configured mock clients."""

    def __init__(self, fixtures_path: Optional[Path] = None):
        """
        Initialize the factory.

        Args:
            fixtures_path: Path to fixtures/responses directory
        """
        self.fixtures_path = fixtures_path or (
            Path(__file__).parent.parent / "fixtures" / "responses"
        )

    def _load_fixture(self, service: str, operation: str) -> Dict[str, Any]:
        """Load a fixture file if it exists."""
        file_path = self.fixtures_path / service / f"{operation}.json"
        if file_path.exists():
            with open(file_path) as f:
                return json.load(f)
        return {}

    def create_slack_client(
        self,
        custom_responses: Optional[Dict[str, Any]] = None
    ) -> MagicMock:
        """
        Create a mocked Slack client.

        Args:
            custom_responses: Override default responses for specific methods

        Returns:
            MagicMock configured as a SlackClient
        """
        mock = MagicMock()
        mock.name = "MockSlackClient"

        # Default responses
        defaults = {
            "list_channels": [
                {"id": "C0001", "name": "general", "is_private": False},
                {"id": "C0002", "name": "random", "is_private": False},
                {"id": "C0003", "name": "test-channel", "is_private": False},
            ],
            "get_channel_info": {
                "id": "C0001",
                "name": "general",
                "is_private": False,
                "topic": {"value": "General discussion"},
                "purpose": {"value": "Company-wide announcements"},
                "num_members": 50,
            },
            "list_users": [
                {"id": "U0001", "name": "testuser", "real_name": "Test User"},
                {"id": "U0002", "name": "botuser", "real_name": "Bot User"},
            ],
            "get_messages": [
                {"ts": "1234567890.123456", "user": "U0001", "text": "Hello world"},
            ],
            "list_pins": [],
            "list_usergroups": [],
            "resolve_channel": "C0001",
            "create_channel": {"id": "C9999", "name": "test-new-channel"},
            "post_message": {"ts": "1234567890.999999", "channel": "C0001"},
            "delete_message": True,
            "archive_channel": True,
            "create_usergroup": {"id": "S0001", "handle": "test-group"},
            "disable_usergroup": {"id": "S0001", "handle": "test-group"},
        }

        # Load fixtures and merge with defaults
        for operation in defaults.keys():
            fixture = self._load_fixture("slack", operation)
            if fixture:
                defaults[operation] = fixture

        # Apply custom responses
        if custom_responses:
            defaults.update(custom_responses)

        # Configure mock methods
        for method, return_value in defaults.items():
            getattr(mock, method).return_value = return_value

        return mock

    def create_notion_client(
        self,
        custom_responses: Optional[Dict[str, Any]] = None
    ) -> MagicMock:
        """
        Create a mocked Notion client.

        Args:
            custom_responses: Override default responses for specific methods

        Returns:
            MagicMock configured as a NotionClient
        """
        mock = MagicMock()
        mock.name = "MockNotionClient"

        defaults = {
            "get_page": {
                "id": "page-001",
                "object": "page",
                "properties": {"title": {"title": [{"text": {"content": "Test Page"}}]}},
            },
            "query_database": {
                "results": [
                    {"id": "row-001", "properties": {}},
                    {"id": "row-002", "properties": {}},
                ],
                "has_more": False,
            },
            # search() returns List[Dict] directly, not a dict with "results" key
            "search": [
                {"id": "result-001", "object": "page"},
            ],
            "list_users": [
                {"id": "user-001", "name": "Test User", "type": "person"},
            ],
            "create_page": {
                "id": "page-new",
                "object": "page",
            },
            "update_page": {
                "id": "page-001",
                "object": "page",
            },
            # archive_page returns the updated page dict, not a boolean
            "archive_page": {
                "id": "page-001",
                "object": "page",
                "archived": True,
            },
            "get_bot_user": {
                "id": "bot-001",
                "object": "user",
                "type": "bot",
            },
            "get_block_children": {
                "results": [],
                "has_more": False,
            },
            "append_blocks": {
                "results": [{"id": "block-new"}],
            },
        }

        for operation in defaults.keys():
            fixture = self._load_fixture("notion", operation)
            if fixture:
                defaults[operation] = fixture

        if custom_responses:
            defaults.update(custom_responses)

        for method, return_value in defaults.items():
            getattr(mock, method).return_value = return_value

        return mock

    def create_n8n_client(
        self,
        custom_responses: Optional[Dict[str, Any]] = None
    ) -> MagicMock:
        """
        Create a mocked n8n client.

        Args:
            custom_responses: Override default responses for specific methods

        Returns:
            MagicMock configured as an N8nClient
        """
        mock = MagicMock()
        mock.name = "MockN8nClient"

        defaults = {
            "list_workflows": [
                {"id": "wf-001", "name": "Test Workflow", "active": False},
                {"id": "wf-002", "name": "Active Workflow", "active": True},
            ],
            "get_workflow": {
                "id": "wf-001",
                "name": "Test Workflow",
                "active": False,
                "nodes": [],
                "connections": {},
            },
            "create_workflow": {
                "id": "wf-new",
                "name": "New Workflow",
            },
            "update_workflow": {
                "id": "wf-001",
                "name": "Updated Workflow",
            },
            "delete_workflow": {},  # Returns empty dict on success
            "activate_workflow": {"id": "wf-001", "active": True},
            "deactivate_workflow": {"id": "wf-001", "active": False},
            # Method is get_executions(), not list_workflow_executions()
            "get_executions": [],
        }

        for operation in defaults.keys():
            fixture = self._load_fixture("n8n", operation)
            if fixture:
                defaults[operation] = fixture

        if custom_responses:
            defaults.update(custom_responses)

        for method, return_value in defaults.items():
            getattr(mock, method).return_value = return_value

        return mock

    def create_cloudflare_client(
        self,
        custom_responses: Optional[Dict[str, Any]] = None
    ) -> MagicMock:
        """
        Create a mocked Cloudflare client.

        Args:
            custom_responses: Override default responses for specific methods

        Returns:
            MagicMock configured as a CloudflareClient
        """
        mock = MagicMock()
        mock.name = "MockCloudflareClient"

        defaults = {
            "list_zones": [
                {"id": "zone-001", "name": "example.com"},
            ],
            "get_zone": {
                "id": "zone-001",
                "name": "example.com",
            },
            "list_dns_records": [
                {"id": "rec-001", "type": "A", "name": "test.example.com", "content": "1.2.3.4"},
            ],
            "get_dns_record": {
                "id": "rec-001",
                "type": "A",
                "name": "test.example.com",
                "content": "1.2.3.4",
            },
            "create_dns_record": {
                "id": "rec-new",
                "type": "A",
                "name": "new.example.com",
                "content": "1.2.3.4",
            },
            "delete_dns_record": True,
            "list_tunnels": [
                {"id": "tunnel-001", "name": "test-tunnel"},
            ],
        }

        for operation in defaults.keys():
            fixture = self._load_fixture("cloudflare", operation)
            if fixture:
                defaults[operation] = fixture

        if custom_responses:
            defaults.update(custom_responses)

        for method, return_value in defaults.items():
            getattr(mock, method).return_value = return_value

        return mock

    def create_dokploy_client(
        self,
        custom_responses: Optional[Dict[str, Any]] = None
    ) -> MagicMock:
        """
        Create a mocked Dokploy client.

        Args:
            custom_responses: Override default responses for specific methods

        Returns:
            MagicMock configured as a DokployClient
        """
        mock = MagicMock()
        mock.name = "MockDokployClient"

        defaults = {
            "list_projects": [
                {"id": "proj-001", "name": "Test Project"},
            ],
            "get_project": {
                "id": "proj-001",
                "name": "Test Project",
            },
            "list_compose_services": [],
            "create_compose": {
                "id": "compose-new",
                "name": "test-compose",
            },
            "delete_compose": True,
            "deploy_compose": True,
        }

        for operation in defaults.keys():
            fixture = self._load_fixture("dokploy", operation)
            if fixture:
                defaults[operation] = fixture

        if custom_responses:
            defaults.update(custom_responses)

        for method, return_value in defaults.items():
            getattr(mock, method).return_value = return_value

        return mock


# Convenience function for quick mock creation
def create_mock_client(service: str, **kwargs) -> MagicMock:
    """
    Create a mock client for the specified service.

    Args:
        service: Service name (slack, notion, n8n, cloudflare, dokploy)
        **kwargs: Custom responses to configure

    Returns:
        Configured MagicMock
    """
    factory = MockClientFactory()

    creators = {
        "slack": factory.create_slack_client,
        "notion": factory.create_notion_client,
        "n8n": factory.create_n8n_client,
        "cloudflare": factory.create_cloudflare_client,
        "dokploy": factory.create_dokploy_client,
    }

    creator = creators.get(service)
    if not creator:
        raise ValueError(f"Unknown service: {service}. Available: {list(creators.keys())}")

    return creator(custom_responses=kwargs if kwargs else None)

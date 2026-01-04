"""
n8n Plugin - Level 2 Tests (Read-Only)
"""
import pytest


@pytest.mark.level2
@pytest.mark.requires_credentials
class TestN8nReadOperations:
    """Read-only tests against real n8n API."""

    def test_list_workflows(self, n8n_client):
        """Test listing workflows."""
        workflows = n8n_client.list_workflows()

        assert isinstance(workflows, list)

    def test_get_workflow(self, n8n_client, find_existing_workflow):
        """Test getting a specific workflow."""
        workflow = find_existing_workflow()
        if not workflow:
            pytest.skip("No workflows available for testing")

        result = n8n_client.get_workflow(workflow["id"])

        assert result["id"] == workflow["id"]
        assert "name" in result

    def test_get_executions(self, n8n_client, find_existing_workflow):
        """Test listing workflow executions."""
        workflow = find_existing_workflow()
        if not workflow:
            pytest.skip("No workflows available for testing")

        # Method is get_executions(), not list_workflow_executions()
        executions = n8n_client.get_executions(workflow_id=workflow["id"])

        assert isinstance(executions, list)

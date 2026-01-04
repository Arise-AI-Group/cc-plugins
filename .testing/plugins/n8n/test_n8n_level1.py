"""
n8n Plugin - Level 1 Tests (Dry/Mocked)
"""
import pytest


class TestN8nMockedOperations:
    """Test operations with mocked responses."""

    @pytest.mark.level1
    def test_list_workflows_returns_list(self, mock_n8n_client):
        """Test that list_workflows returns a list."""
        workflows = mock_n8n_client.list_workflows()

        assert isinstance(workflows, list)

    @pytest.mark.level1
    def test_get_workflow_returns_dict(self, mock_n8n_client):
        """Test that get_workflow returns workflow details."""
        workflow = mock_n8n_client.get_workflow("wf-001")

        assert isinstance(workflow, dict)
        assert "id" in workflow
        assert "name" in workflow

    @pytest.mark.level1
    def test_create_workflow_returns_workflow(self, mock_n8n_client):
        """Test that create_workflow returns workflow details."""
        workflow = mock_n8n_client.create_workflow({})

        assert isinstance(workflow, dict)
        assert "id" in workflow

    @pytest.mark.level1
    def test_delete_workflow_succeeds(self, mock_n8n_client):
        """Test that delete_workflow completes without error."""
        # delete_workflow returns empty dict on success
        result = mock_n8n_client.delete_workflow("wf-001")

        assert isinstance(result, dict)

    @pytest.mark.level1
    def test_activate_workflow_returns_workflow(self, mock_n8n_client):
        """Test that activate_workflow returns workflow details."""
        result = mock_n8n_client.activate_workflow("wf-001")

        assert isinstance(result, dict)
        assert result.get("active") is True

    @pytest.mark.level1
    def test_deactivate_workflow_returns_workflow(self, mock_n8n_client):
        """Test that deactivate_workflow returns workflow details."""
        result = mock_n8n_client.deactivate_workflow("wf-001")

        assert isinstance(result, dict)
        assert result.get("active") is False

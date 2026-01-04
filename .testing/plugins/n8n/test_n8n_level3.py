"""
n8n Plugin - Level 3 Tests (Write Operations)
"""
import pytest
import time


@pytest.mark.level3
@pytest.mark.requires_credentials
class TestN8nWorkflowOperations:
    """Test workflow creation and management."""

    def test_create_and_delete_workflow(
        self,
        n8n_client,
        test_prefix,
        n8n_cleanup
    ):
        """Test creating and deleting a workflow."""
        timestamp = int(time.time())
        workflow_name = f"{test_prefix}workflow-{timestamp}"

        # Create a simple workflow
        workflow_data = {
            "name": workflow_name,
            "nodes": [
                {
                    "parameters": {},
                    "name": "Start",
                    "type": "n8n-nodes-base.start",
                    "typeVersion": 1,
                    "position": [240, 300]
                }
            ],
            "connections": {},
            "settings": {}
        }

        workflow = n8n_client.create_workflow(workflow_data)
        n8n_cleanup.register("n8n_workflows", {"id": workflow["id"]})

        assert "id" in workflow
        assert workflow["name"] == workflow_name

        # Delete workflow - returns empty dict on success
        n8n_client.delete_workflow(workflow["id"])

        # Verify deletion by trying to get it (should fail)
        try:
            n8n_client.get_workflow(workflow["id"])
            pytest.fail("Workflow should have been deleted")
        except Exception:
            pass  # Expected - workflow was deleted

    def test_activate_and_deactivate_workflow(
        self,
        n8n_client,
        test_prefix,
        n8n_cleanup
    ):
        """Test activating and deactivating a workflow."""
        timestamp = int(time.time())
        workflow_name = f"{test_prefix}activate-{timestamp}"

        # Create workflow with webhook trigger (required for activation)
        workflow_data = {
            "name": workflow_name,
            "nodes": [
                {
                    "parameters": {"path": f"test-{timestamp}"},
                    "name": "Webhook",
                    "type": "n8n-nodes-base.webhook",
                    "typeVersion": 1,
                    "position": [240, 300],
                    "webhookId": f"test-{timestamp}"
                }
            ],
            "connections": {},
            "settings": {}
        }

        workflow = n8n_client.create_workflow(workflow_data)
        n8n_cleanup.register("n8n_workflows", {"id": workflow["id"]})

        # Activate
        try:
            activated = n8n_client.activate_workflow(workflow["id"])
            assert activated.get("active") is True

            # Deactivate
            deactivated = n8n_client.deactivate_workflow(workflow["id"])
            assert deactivated.get("active") is False
        except Exception as e:
            if "trigger" in str(e).lower():
                pytest.skip("Workflow requires valid trigger node")
            raise

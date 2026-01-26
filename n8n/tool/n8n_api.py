#!/usr/bin/env python3
"""
n8n API Integration Script

Execution tool for managing n8n workflows via the REST API.
Supports: list, get, create, update, activate, deactivate, execute, and get execution results.
Supports multiple n8n instances via profiles.

Usage (CLI):
    ./run tool/n8n_api.py [--profile <name>] list
    ./run tool/n8n_api.py [--profile <name>] get <workflow_id>
    ./run tool/n8n_api.py [--profile <name>] create <json_file>
    ./run tool/n8n_api.py [--profile <name>] update <workflow_id> <json_file>
    ./run tool/n8n_api.py [--profile <name>] activate <workflow_id>
    ./run tool/n8n_api.py [--profile <name>] deactivate <workflow_id>
    ./run tool/n8n_api.py [--profile <name>] execute <workflow_id> [input_json]
    ./run tool/n8n_api.py [--profile <name>] executions <workflow_id> [limit]
    ./run tool/n8n_api.py [--profile <name>] execution <execution_id> [--full]
    ./run tool/n8n_api.py [--profile <name>] export <workflow_id> <output_file>
    ./run tool/n8n_api.py [--profile <name>] delete <workflow_id>
    ./run tool/n8n_api.py [--profile <name>] info <workflow_id>

Profile Management:
    ./run tool/n8n_api.py profile list
    ./run tool/n8n_api.py profile add <name> --url <url> --api-key-env <ENV_VAR> [--description <desc>]
    ./run tool/n8n_api.py profile default <name>
    ./run tool/n8n_api.py profile remove <name>

IMPORTANT: The n8n public API does not support direct workflow execution.
The 'execute' command works by calling the workflow's webhook trigger.
Workflows must have a webhook trigger and be activated to use 'execute'.
Use 'info' to see how to test a specific workflow.

Usage (Module):
    from tool.n8n_api import N8nClient
    client = N8nClient()  # Uses default profile or env vars
    client = N8nClient(profile="staging")  # Uses specific profile
    workflows = client.list_workflows()
"""

import sys
import os
import json
import requests
from pathlib import Path
from typing import Optional, Dict, List, Any

from .config import get_api_key
from . import profiles


class N8nClient:
    """Client for interacting with n8n REST API."""

    def __init__(self, base_url: str = None, api_key: str = None, profile: str = None):
        """
        Initialize n8n client.

        Args:
            base_url: Override API URL
            api_key: Override API key
            profile: Profile name to use (from n8n.json)

        If base_url and api_key are not provided, credentials are resolved from:
        1. Specified profile (if profile arg provided)
        2. Default profile from n8n.json
        3. N8N_API_URL/N8N_API_KEY environment variables
        """
        if base_url and api_key:
            self.base_url = base_url.rstrip("/")
            self.api_key = api_key
        else:
            self.base_url, self.api_key = profiles.resolve_credentials(profile)

        self.headers = {
            "X-N8N-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make an API request."""
        url = f"{self.base_url}/api/v1{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            raise Exception(f"n8n API error: {error_msg}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")

    # --- Workflow Operations ---

    def list_workflows(self, active: bool = None, tags: List[str] = None) -> List[dict]:
        """List all workflows."""
        params = []
        if active is not None:
            params.append(f"active={str(active).lower()}")
        if tags:
            params.append(f"tags={','.join(tags)}")

        endpoint = "/workflows"
        if params:
            endpoint += "?" + "&".join(params)

        result = self._request("GET", endpoint)
        return result.get("data", [])

    def get_workflow(self, workflow_id: str) -> dict:
        """Get a specific workflow by ID."""
        return self._request("GET", f"/workflows/{workflow_id}")

    def create_workflow(self, workflow_data: dict) -> dict:
        """Create a new workflow from JSON data."""
        # Remove fields that shouldn't be in create request
        clean_data = {k: v for k, v in workflow_data.items()
                      if k not in ["id", "createdAt", "updatedAt"]}
        return self._request("POST", "/workflows", clean_data)

    def update_workflow(self, workflow_id: str, workflow_data: dict) -> dict:
        """Update an existing workflow."""
        # Remove fields that shouldn't be in update request
        # The n8n API only accepts: name, nodes, connections, settings, staticData
        allowed_fields = ["name", "nodes", "connections", "settings", "staticData"]
        clean_data = {k: v for k, v in workflow_data.items()
                      if k in allowed_fields}
        return self._request("PUT", f"/workflows/{workflow_id}", clean_data)

    def delete_workflow(self, workflow_id: str) -> dict:
        """Delete a workflow."""
        return self._request("DELETE", f"/workflows/{workflow_id}")

    def activate_workflow(self, workflow_id: str) -> dict:
        """Activate a workflow."""
        return self._request("POST", f"/workflows/{workflow_id}/activate")

    def deactivate_workflow(self, workflow_id: str) -> dict:
        """Deactivate a workflow."""
        return self._request("POST", f"/workflows/{workflow_id}/deactivate")

    # --- Execution Operations ---

    def execute_workflow(self, workflow_id: str, input_data: dict = None) -> dict:
        """
        Execute a workflow via its webhook trigger.

        IMPORTANT: The n8n public API does not support direct workflow execution.
        This method looks for a webhook trigger in the workflow and calls it.

        For workflows without webhook triggers, you must:
        1. Add a webhook trigger node to the workflow
        2. Activate the workflow
        3. Use this method to trigger it

        Args:
            workflow_id: The workflow ID to execute
            input_data: Optional JSON data to send to the webhook

        Returns:
            The webhook response
        """
        # Get the workflow to find its webhook URL
        workflow = self.get_workflow(workflow_id)

        # Look for webhook nodes
        webhook_nodes = [
            node for node in workflow.get("nodes", [])
            if node.get("type") in ["n8n-nodes-base.webhook", "n8n-nodes-base.webhookTrigger"]
        ]

        if not webhook_nodes:
            raise Exception(
                f"Workflow '{workflow.get('name')}' has no webhook trigger. "
                "The n8n public API does not support direct execution. "
                "To execute via API, add a Webhook node to your workflow and activate it."
            )

        if not workflow.get("active"):
            raise Exception(
                f"Workflow '{workflow.get('name')}' is not active. "
                f"Activate it first with: ./run tool/n8n_api.py activate {workflow_id}"
            )

        # Get webhook path from the first webhook node
        webhook_node = webhook_nodes[0]
        webhook_path = webhook_node.get("parameters", {}).get("path", "")
        webhook_id = webhook_node.get("webhookId", "")

        if not webhook_path and not webhook_id:
            raise Exception("Could not determine webhook URL from workflow.")

        # Construct webhook URL
        # n8n webhook URLs follow pattern: {base_url}/webhook/{path} or /webhook-test/{path}
        webhook_url = f"{self.base_url}/webhook/{webhook_path}"

        try:
            response = requests.post(
                webhook_url,
                headers={"Content-Type": "application/json"},
                json=input_data or {},
                timeout=60
            )
            response.raise_for_status()
            return response.json() if response.text else {"status": "triggered", "statusCode": response.status_code}
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            raise Exception(f"Webhook call failed: {error_msg}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")

    def test_workflow(self, workflow_id: str) -> dict:
        """
        Get information about how to test a workflow.

        Since n8n's public API doesn't support direct execution, this method
        provides guidance on how to test the workflow.
        """
        workflow = self.get_workflow(workflow_id)

        # Analyze the workflow
        nodes = workflow.get("nodes", [])
        trigger_nodes = [n for n in nodes if "trigger" in n.get("type", "").lower() or n.get("type") == "n8n-nodes-base.webhook"]

        result = {
            "workflow_id": workflow_id,
            "name": workflow.get("name"),
            "active": workflow.get("active"),
            "trigger_count": len(trigger_nodes),
            "triggers": []
        }

        for node in trigger_nodes:
            node_type = node.get("type", "")
            trigger_info = {"name": node.get("name"), "type": node_type}

            if "webhook" in node_type.lower():
                path = node.get("parameters", {}).get("path", "")
                trigger_info["webhook_url"] = f"{self.base_url}/webhook/{path}"
                trigger_info["test_url"] = f"{self.base_url}/webhook-test/{path}"

            result["triggers"].append(trigger_info)

        if not trigger_nodes:
            result["note"] = "This workflow has no triggers. It can only be executed manually in the n8n UI."
        elif not workflow.get("active"):
            result["note"] = "Workflow is inactive. Activate it to enable webhook triggers."

        return result

    def get_executions(self, workflow_id: str = None, limit: int = 20) -> List[dict]:
        """Get execution history."""
        params = [f"limit={limit}"]
        if workflow_id:
            params.append(f"workflowId={workflow_id}")

        endpoint = "/executions?" + "&".join(params)
        result = self._request("GET", endpoint)
        return result.get("data", [])

    def get_execution(self, execution_id: str, include_data: bool = True) -> dict:
        """Get details of a specific execution."""
        endpoint = f"/executions/{execution_id}"
        if include_data:
            endpoint += "?includeData=true"
        return self._request("GET", endpoint)

    # --- Convenience Methods ---

    def deploy_from_file(self, json_path: str, workflow_id: str = None) -> dict:
        """
        Deploy a workflow from a local JSON file.
        If workflow_id is provided, updates existing workflow.
        Otherwise, creates a new workflow.
        """
        with open(json_path, 'r') as f:
            workflow_data = json.load(f)

        if workflow_id:
            print(f"Updating workflow {workflow_id} from {json_path}...")
            return self.update_workflow(workflow_id, workflow_data)
        else:
            print(f"Creating new workflow from {json_path}...")
            return self.create_workflow(workflow_data)

    def export_to_file(self, workflow_id: str, output_path: str) -> str:
        """Export a workflow to a local JSON file."""
        workflow = self.get_workflow(workflow_id)

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(workflow, f, indent=2)

        return output_path


# --- CLI Interface ---

def print_workflow_summary(workflow: dict):
    """Print a summary of a workflow."""
    print(f"  ID: {workflow.get('id')}")
    print(f"  Name: {workflow.get('name')}")
    print(f"  Active: {workflow.get('active', False)}")
    if workflow.get('tags'):
        print(f"  Tags: {', '.join(t.get('name', '') for t in workflow.get('tags', []))}")
    print()


def handle_profile_command(args: List[str]) -> None:
    """Handle profile management commands."""
    if len(args) < 1:
        print("Profile commands:")
        print("  profile list                                    - List all profiles")
        print("  profile add <name> --url <url> --api-key-env <ENV_VAR> [--description <desc>]")
        print("  profile default <name>                          - Set default profile")
        print("  profile remove <name>                           - Remove a profile")
        sys.exit(1)

    subcommand = args[0]

    if subcommand == "list":
        config = profiles.get_n8n_config()
        profile_list = profiles.list_profiles()
        default_name = profiles.get_default_profile_name()

        if not profile_list:
            print("\nNo profiles configured.")
            print("\nUsing environment variables:")
            api_url = get_api_key("N8N_API_URL")
            if api_url:
                print(f"  N8N_API_URL: {api_url}")
                print(f"  N8N_API_KEY: {'(set)' if get_api_key('N8N_API_KEY') else '(not set)'}")
            else:
                print("  No N8N_API_URL configured")
            print("\nTo add a profile:")
            print("  ./run tool/n8n_api.py profile add production --url https://n8n.example.com --api-key-env N8N_PROD_API_KEY")
            return

        print(f"\nConfigured profiles ({len(profile_list)}):\n")
        for name, profile in profile_list.items():
            default_marker = " (default)" if name == default_name else ""
            desc = f" - {profile.description}" if profile.description else ""
            key_status = "(key set)" if profile.api_key else "(key missing)"
            print(f"  {name}{default_marker}: {profile.api_url} {key_status}{desc}")

        print()

    elif subcommand == "add":
        if len(args) < 2:
            print("Usage: profile add <name> --url <url> --api-key-env <ENV_VAR> [--description <desc>]")
            sys.exit(1)

        name = args[1]
        url = None
        api_key_env = None
        description = None

        # Parse remaining args
        i = 2
        while i < len(args):
            if args[i] == "--url" and i + 1 < len(args):
                url = args[i + 1]
                i += 2
            elif args[i] == "--api-key-env" and i + 1 < len(args):
                api_key_env = args[i + 1]
                i += 2
            elif args[i] == "--description" and i + 1 < len(args):
                description = args[i + 1]
                i += 2
            else:
                i += 1

        if not url:
            print("Error: --url is required")
            sys.exit(1)
        if not api_key_env:
            print("Error: --api-key-env is required")
            sys.exit(1)

        profiles.add_profile(name, url, api_key_env, description)
        print(f"Added profile: {name}")
        print(f"  URL: {url}")
        print(f"  API Key Env: {api_key_env}")
        if description:
            print(f"  Description: {description}")

        # Check if the env var is set
        if not get_api_key(api_key_env):
            print(f"\nWarning: {api_key_env} is not set in ~/.config/cc-plugins/.env")
            print(f"Add it with: echo '{api_key_env}=your_api_key' >> ~/.config/cc-plugins/.env")

    elif subcommand == "default":
        if len(args) < 2:
            print("Usage: profile default <name>")
            sys.exit(1)

        name = args[1]
        if profiles.set_default_profile(name):
            print(f"Set default profile: {name}")
        else:
            print(f"Error: Profile '{name}' not found")
            sys.exit(1)

    elif subcommand == "remove":
        if len(args) < 2:
            print("Usage: profile remove <name>")
            sys.exit(1)

        name = args[1]
        if profiles.remove_profile(name):
            print(f"Removed profile: {name}")
        else:
            print(f"Error: Profile '{name}' not found")
            sys.exit(1)

    else:
        print(f"Unknown profile command: {subcommand}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # Parse --profile flag
    args = sys.argv[1:]
    profile_name = None

    if args[0] == "--profile":
        if len(args) < 3:
            print("Usage: ./run tool/n8n_api.py --profile <name> <command> [args...]")
            sys.exit(1)
        profile_name = args[1]
        args = args[2:]

    if not args:
        print(__doc__)
        sys.exit(1)

    command = args[0].lower()

    # Handle profile command separately (no client needed)
    if command == "profile":
        handle_profile_command(args[1:])
        return

    # Create client with profile
    try:
        client = N8nClient(profile=profile_name)
        if profile_name:
            print(f"[Using profile: {profile_name}]\n")
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    try:
        if command == "list":
            print("Fetching workflows...")
            workflows = client.list_workflows()
            print(f"\nFound {len(workflows)} workflow(s):\n")
            for wf in workflows:
                print_workflow_summary(wf)

        elif command == "get":
            if len(args) < 2:
                print("Usage: ./run tool/n8n_api.py get <workflow_id>")
                sys.exit(1)
            workflow_id = args[1]
            workflow = client.get_workflow(workflow_id)
            print(json.dumps(workflow, indent=2))

        elif command == "create":
            if len(args) < 2:
                print("Usage: ./run tool/n8n_api.py create <json_file>")
                sys.exit(1)
            json_file = args[1]
            result = client.deploy_from_file(json_file)
            print(f"Created workflow: {result.get('id')} - {result.get('name')}")

        elif command == "update":
            if len(args) < 3:
                print("Usage: ./run tool/n8n_api.py update <workflow_id> <json_file>")
                sys.exit(1)
            workflow_id = args[1]
            json_file = args[2]
            result = client.deploy_from_file(json_file, workflow_id)
            print(f"Updated workflow: {result.get('id')} - {result.get('name')}")

        elif command == "activate":
            if len(args) < 2:
                print("Usage: ./run tool/n8n_api.py activate <workflow_id>")
                sys.exit(1)
            workflow_id = args[1]
            result = client.activate_workflow(workflow_id)
            print(f"Activated workflow: {workflow_id}")

        elif command == "deactivate":
            if len(args) < 2:
                print("Usage: ./run tool/n8n_api.py deactivate <workflow_id>")
                sys.exit(1)
            workflow_id = args[1]
            result = client.deactivate_workflow(workflow_id)
            print(f"Deactivated workflow: {workflow_id}")

        elif command == "execute":
            if len(args) < 2:
                print("Usage: ./run tool/n8n_api.py execute <workflow_id> [input_json]")
                sys.exit(1)
            workflow_id = args[1]
            input_data = None
            if len(args) > 2:
                input_data = json.loads(args[2])

            print(f"Executing workflow {workflow_id}...")
            result = client.execute_workflow(workflow_id, input_data)
            print(f"Execution started: {result.get('id', 'unknown')}")
            print(json.dumps(result, indent=2))

        elif command == "executions":
            workflow_id = args[1] if len(args) > 1 else None
            limit = int(args[2]) if len(args) > 2 else 20

            executions = client.get_executions(workflow_id, limit)
            print(f"\nLast {len(executions)} execution(s):\n")
            for ex in executions:
                status = ex.get('status', 'unknown')
                marker = "OK" if status == "success" else "ERR" if status == "error" else "  "
                print(f"  [{marker}] {ex.get('id')} | {ex.get('workflowId')} | {status} | {ex.get('startedAt', 'N/A')}")

        elif command == "execution":
            if len(args) < 2:
                print("Usage: ./run tool/n8n_api.py execution <execution_id> [--full]")
                sys.exit(1)
            execution_id = args[1]
            execution = client.get_execution(execution_id)

            # Print summary
            status = execution.get('status', 'unknown')
            print(f"\nExecution {execution_id}:")
            print(f"  Status: {status}")
            print(f"  Workflow: {execution.get('workflowId')}")
            print(f"  Started: {execution.get('startedAt', 'N/A')}")
            print(f"  Finished: {execution.get('stoppedAt', 'N/A')}")

            # Print error if present
            result_data = execution.get('data', {}).get('resultData', {})
            error = result_data.get('error', {})
            if error:
                print(f"\n  ERROR:")
                print(f"    Message: {error.get('message', 'No message')}")
                print(f"    Node: {error.get('node', 'Unknown')}")
                if error.get('description'):
                    print(f"    Description: {error.get('description')}")

            # Option to print full JSON
            if len(args) > 2 and args[2] == "--full":
                print("\nFull execution data:")
                print(json.dumps(execution, indent=2))

        elif command == "export":
            if len(args) < 3:
                print("Usage: ./run tool/n8n_api.py export <workflow_id> <output_file>")
                sys.exit(1)
            workflow_id = args[1]
            output_file = args[2]
            path = client.export_to_file(workflow_id, output_file)
            print(f"Exported workflow {workflow_id} to {path}")

        elif command == "delete":
            if len(args) < 2:
                print("Usage: ./run tool/n8n_api.py delete <workflow_id>")
                sys.exit(1)
            workflow_id = args[1]
            confirm = input(f"Delete workflow {workflow_id}? (yes/no): ")
            if confirm.lower() == "yes":
                client.delete_workflow(workflow_id)
                print(f"Deleted workflow: {workflow_id}")
            else:
                print("Cancelled.")

        elif command == "info":
            if len(args) < 2:
                print("Usage: ./run tool/n8n_api.py info <workflow_id>")
                sys.exit(1)
            workflow_id = args[1]
            info = client.test_workflow(workflow_id)
            print(f"\nWorkflow: {info['name']}")
            print(f"ID: {info['workflow_id']}")
            print(f"Active: {info['active']}")
            print(f"Triggers: {info['trigger_count']}")
            if info.get('note'):
                print(f"\nNote: {info['note']}")
            if info['triggers']:
                print("\nTrigger details:")
                for t in info['triggers']:
                    print(f"  - {t['name']} ({t['type']})")
                    if t.get('webhook_url'):
                        print(f"    Production: {t['webhook_url']}")
                        print(f"    Test: {t['test_url']}")

        else:
            print(f"Unknown command: {command}")
            print(__doc__)
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

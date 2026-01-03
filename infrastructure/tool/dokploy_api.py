#!/usr/bin/env python3
"""
Dokploy API Integration Script

Execution tool for managing Dokploy compose services via the REST API.
Complements the Dokploy MCP tools which don't expose compose creation.

Usage (CLI):
    ./run tool/dokploy_api.py project list
    ./run tool/dokploy_api.py project get <project_id>
    ./run tool/dokploy_api.py compose create <environment_id> <name> --file compose.yaml
    ./run tool/dokploy_api.py compose create <environment_id> <name> --yaml "services:..."
    ./run tool/dokploy_api.py compose update <compose_id> --file compose.yaml --env "KEY=value"
    ./run tool/dokploy_api.py compose deploy <compose_id>
    ./run tool/dokploy_api.py compose get <compose_id>
    ./run tool/dokploy_api.py compose delete <compose_id>
    ./run tool/dokploy_api.py domain create <compose_id> <host> <port> <service_name>

Usage (Module):
    from tool.dokploy_api import DokployClient
    client = DokployClient()
    compose = client.create_compose("env-id", "my-app", compose_file="services:\\n  app:...")
    client.update_compose(compose["composeId"], env="KEY=value\\nKEY2=value2")
    client.deploy_compose(compose["composeId"])
"""

import sys
import os
import json
import argparse
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List

from .config import get_api_key

# Get API credentials (shared config handles fallback chain)
DOKPLOY_API_URL = get_api_key("DOKPLOY_URL") or get_api_key("DOKPLOY_API_URL")
DOKPLOY_API_KEY = get_api_key("DOKPLOY_API_KEY")


# --- Custom Exceptions ---

class DokployError(Exception):
    """Base exception for Dokploy API errors."""
    pass


class DokployAuthError(DokployError):
    """Authentication/token error."""
    pass


class DokployNotFoundError(DokployError):
    """Resource not found."""
    pass


class DokployClient:
    """Client for interacting with Dokploy API."""

    def __init__(self, api_url: str = None, api_key: str = None):
        self.api_url = (api_url or DOKPLOY_API_URL).rstrip("/")
        self.api_key = api_key or DOKPLOY_API_KEY

        if not self.api_url:
            raise ValueError("DOKPLOY_URL not configured. Set it in .env or .mcp.json")
        if not self.api_key:
            raise ValueError("DOKPLOY_API_KEY not configured. Set it in .env or .mcp.json")

        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make an API request to Dokploy."""
        url = f"{self.api_url}{endpoint}"

        if method == "GET":
            # GET uses query parameters
            response = requests.get(url, headers=self.headers, params=data)
        else:
            # POST uses JSON body
            response = requests.post(url, headers=self.headers, json=data)

        if response.status_code == 401:
            raise DokployAuthError("Authentication failed. Check your API key.")
        elif response.status_code == 404:
            raise DokployNotFoundError(f"Resource not found: {endpoint}")
        elif response.status_code == 400:
            try:
                error_data = response.json()
                raise DokployError(f"Validation error: {error_data.get('message', response.text)}")
            except json.JSONDecodeError:
                raise DokployError(f"Bad request: {response.text}")

        try:
            result = response.json()
        except json.JSONDecodeError:
            raise DokployError(f"Invalid JSON response: {response.text}")

        # Handle error responses
        if isinstance(result, dict) and "error" in result:
            error_msg = result["error"].get("message", str(result["error"]))
            raise DokployError(f"API error: {error_msg}")

        return result

    # --- Compose Operations ---

    def create_compose(
        self,
        environment_id: str,
        name: str,
        compose_file: str = None,
        description: str = None,
        server_id: str = None
    ) -> Dict[str, Any]:
        """
        Create a new compose service.

        Args:
            environment_id: ID of the environment to create in
            name: Name for the compose service
            compose_file: Optional initial compose YAML content
            description: Optional description
            server_id: Optional server ID for remote deployment

        Returns:
            Created compose service details
        """
        data = {
            "name": name,
            "environmentId": environment_id,
        }

        if server_id:
            data["serverId"] = server_id

        result = self._request("POST", "/compose.create", data)

        # If compose_file provided, update it immediately
        if compose_file and result.get("composeId"):
            self.update_compose(
                result["composeId"],
                compose_file=compose_file,
                source_type="raw"
            )
            # Re-fetch to get updated data
            result = self.get_compose(result["composeId"])

        return result

    def get_compose(self, compose_id: str) -> Dict[str, Any]:
        """Get compose service details."""
        return self._request("GET", "/compose.one", {"composeId": compose_id})

    def update_compose(
        self,
        compose_id: str,
        name: str = None,
        description: str = None,
        compose_file: str = None,
        env: str = None,
        source_type: str = None,
        compose_path: str = None
    ) -> Dict[str, Any]:
        """
        Update a compose service.

        Args:
            compose_id: ID of the compose service
            name: New name
            description: New description
            compose_file: New compose YAML content
            env: Environment variables (newline-separated KEY=value pairs)
            source_type: Source type ("raw", "github", etc.)
            compose_path: Path to compose file in repo

        Returns:
            Updated compose service details
        """
        data = {"composeId": compose_id}

        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if compose_file is not None:
            data["composeFile"] = compose_file
        if env is not None:
            data["env"] = env
        if source_type is not None:
            data["sourceType"] = source_type
        if compose_path is not None:
            data["composePath"] = compose_path

        return self._request("POST", "/compose.update", data)

    def deploy_compose(self, compose_id: str, title: str = None, description: str = None) -> Dict[str, Any]:
        """Deploy a compose service."""
        data = {"composeId": compose_id}
        if title:
            data["title"] = title
        if description:
            data["description"] = description

        return self._request("POST", "/compose.deploy", data)

    def delete_compose(self, compose_id: str) -> bool:
        """Delete a compose service."""
        self._request("POST", "/compose.delete", {"composeId": compose_id})
        return True

    def stop_compose(self, compose_id: str) -> Dict[str, Any]:
        """Stop a compose service."""
        return self._request("POST", "/compose.stop", {"composeId": compose_id})

    def start_compose(self, compose_id: str) -> Dict[str, Any]:
        """Start a compose service."""
        return self._request("POST", "/compose.start", {"composeId": compose_id})

    # --- Project/Environment Operations ---

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects in Dokploy."""
        return self._request("GET", "/project.all")

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details including environments."""
        return self._request("GET", "/project.one", {"projectId": project_id})

    # --- Domain Operations ---

    def create_domain(
        self,
        compose_id: str,
        host: str,
        port: int,
        service_name: str,
        path: str = "/"
    ) -> Dict[str, Any]:
        """
        Add domain routing for a compose service.

        Args:
            compose_id: ID of the compose service
            host: Full hostname (e.g., "cal.arisegroup-tools.com")
            port: Internal container port
            service_name: Service name from docker-compose.yml
            path: URL path (default: "/")

        Returns:
            Created domain details
        """
        return self._request("POST", "/domain.create", {
            "composeId": compose_id,
            "host": host,
            "port": port,
            "serviceName": service_name,
            "domainType": "compose",
            "https": False,  # Cloudflare handles TLS
            "path": path
        })

    def list_domains(self, compose_id: str) -> List[Dict[str, Any]]:
        """List domains configured for a compose service."""
        try:
            return self._request("GET", "/domain.byComposeId", {"composeId": compose_id})
        except DokployError:
            return []


# --- CLI Interface ---

def cmd_compose_create(args, client: DokployClient):
    """Create a compose service."""
    compose_file = None

    if args.file:
        with open(args.file) as f:
            compose_file = f.read()
    elif args.yaml:
        compose_file = args.yaml

    result = client.create_compose(
        environment_id=args.environment_id,
        name=args.name,
        compose_file=compose_file,
        description=args.description
    )

    print(f"Created compose service:")
    print(f"  ID: {result.get('composeId')}")
    print(f"  Name: {result.get('name')}")
    print(f"  App Name: {result.get('appName')}")

    if args.env:
        # Update with env vars
        client.update_compose(result["composeId"], env=args.env)
        print(f"  Environment variables set")

    return result


def cmd_compose_update(args, client: DokployClient):
    """Update a compose service."""
    compose_file = None

    if args.file:
        with open(args.file) as f:
            compose_file = f.read()
    elif args.yaml:
        compose_file = args.yaml

    result = client.update_compose(
        compose_id=args.compose_id,
        name=args.name,
        description=args.description,
        compose_file=compose_file,
        env=args.env,
        source_type="raw" if compose_file else None
    )

    print(f"Updated compose service: {args.compose_id}")
    return result


def cmd_compose_deploy(args, client: DokployClient):
    """Deploy a compose service."""
    result = client.deploy_compose(
        compose_id=args.compose_id,
        title=args.title,
        description=args.description
    )

    print(f"Deployment initiated for: {args.compose_id}")
    return result


def cmd_compose_get(args, client: DokployClient):
    """Get compose service details."""
    result = client.get_compose(args.compose_id)

    print(f"Compose Service: {result.get('name')}")
    print(f"  ID: {result.get('composeId')}")
    print(f"  App Name: {result.get('appName')}")
    print(f"  Status: {result.get('composeStatus')}")
    print(f"  Source Type: {result.get('sourceType')}")

    if args.verbose:
        print(f"\nCompose File:")
        print(result.get('composeFile', '(empty)'))
        print(f"\nEnvironment Variables:")
        print(result.get('env', '(none)'))

    return result


def cmd_compose_delete(args, client: DokployClient):
    """Delete a compose service."""
    if not args.yes:
        confirm = input(f"Are you sure you want to delete compose {args.compose_id}? [y/N] ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return

    client.delete_compose(args.compose_id)
    print(f"Deleted compose service: {args.compose_id}")


def cmd_project_list(args, client: DokployClient):
    """List all projects and their environments."""
    projects = client.list_projects()

    if not projects:
        print("No projects found.")
        return

    for project in projects:
        print(f"\nProject: {project.get('name')}")
        print(f"  ID: {project.get('projectId')}")

        # Get full project details to list environments
        try:
            details = client.get_project(project.get('projectId'))
            environments = details.get('environments', [])
            if environments:
                print(f"  Environments:")
                for env in environments:
                    print(f"    - {env.get('name')}: {env.get('environmentId')}")
        except DokployError:
            pass


def cmd_project_get(args, client: DokployClient):
    """Get project details."""
    project = client.get_project(args.project_id)

    print(f"Project: {project.get('name')}")
    print(f"  ID: {project.get('projectId')}")
    print(f"  Description: {project.get('description', '(none)')}")

    environments = project.get('environments', [])
    if environments:
        print(f"\n  Environments:")
        for env in environments:
            print(f"    {env.get('name')}:")
            print(f"      ID: {env.get('environmentId')}")
            composes = env.get('compose', [])
            if composes:
                print(f"      Compose services:")
                for compose in composes:
                    print(f"        - {compose.get('name')} ({compose.get('composeId')})")


def cmd_domain_create(args, client: DokployClient):
    """Create a domain for a compose service."""
    result = client.create_domain(
        compose_id=args.compose_id,
        host=args.host,
        port=int(args.port),
        service_name=args.service_name,
        path=args.path or "/"
    )

    print(f"Created domain:")
    print(f"  ID: {result.get('domainId')}")
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  Service: {args.service_name}")
    print(f"  HTTPS: OFF (Cloudflare handles TLS)")
    print(f"\nIMPORTANT: Redeploy the compose service to apply domain routing!")

    return result


def cmd_domain_list(args, client: DokployClient):
    """List domains for a compose service."""
    domains = client.list_domains(args.compose_id)

    if not domains:
        print("No domains configured.")
        return

    for domain in domains:
        print(f"\nDomain: {domain.get('host')}")
        print(f"  ID: {domain.get('domainId')}")
        print(f"  Port: {domain.get('port')}")
        print(f"  Service: {domain.get('serviceName')}")
        print(f"  HTTPS: {domain.get('https', False)}")


def main():
    parser = argparse.ArgumentParser(description="Dokploy API CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command group")

    # --- Compose commands ---
    compose_parser = subparsers.add_parser("compose", help="Compose service operations")
    compose_sub = compose_parser.add_subparsers(dest="subcommand")

    # compose create
    compose_create = compose_sub.add_parser("create", help="Create compose service")
    compose_create.add_argument("environment_id", help="Environment ID")
    compose_create.add_argument("name", help="Service name")
    compose_create.add_argument("--file", "-f", help="Path to compose YAML file")
    compose_create.add_argument("--yaml", help="Compose YAML content directly")
    compose_create.add_argument("--env", "-e", help="Environment variables (KEY=value, newline-separated)")
    compose_create.add_argument("--description", "-d", help="Service description")

    # compose update
    compose_update = compose_sub.add_parser("update", help="Update compose service")
    compose_update.add_argument("compose_id", help="Compose service ID")
    compose_update.add_argument("--file", "-f", help="Path to compose YAML file")
    compose_update.add_argument("--yaml", help="Compose YAML content directly")
    compose_update.add_argument("--env", "-e", help="Environment variables")
    compose_update.add_argument("--name", help="New name")
    compose_update.add_argument("--description", "-d", help="New description")

    # compose deploy
    compose_deploy = compose_sub.add_parser("deploy", help="Deploy compose service")
    compose_deploy.add_argument("compose_id", help="Compose service ID")
    compose_deploy.add_argument("--title", help="Deployment title")
    compose_deploy.add_argument("--description", "-d", help="Deployment description")

    # compose get
    compose_get = compose_sub.add_parser("get", help="Get compose service details")
    compose_get.add_argument("compose_id", help="Compose service ID")
    compose_get.add_argument("--verbose", "-v", action="store_true", help="Show full details")

    # compose delete
    compose_delete = compose_sub.add_parser("delete", help="Delete compose service")
    compose_delete.add_argument("compose_id", help="Compose service ID")
    compose_delete.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    # compose start
    compose_start = compose_sub.add_parser("start", help="Start compose service")
    compose_start.add_argument("compose_id", help="Compose service ID")

    # compose stop
    compose_stop = compose_sub.add_parser("stop", help="Stop compose service")
    compose_stop.add_argument("compose_id", help="Compose service ID")

    # --- Project commands ---
    project_parser = subparsers.add_parser("project", help="Project operations")
    project_sub = project_parser.add_subparsers(dest="subcommand")

    # project list
    project_sub.add_parser("list", help="List all projects and environments")

    # project get
    project_get = project_sub.add_parser("get", help="Get project details")
    project_get.add_argument("project_id", help="Project ID")

    # --- Domain commands ---
    domain_parser = subparsers.add_parser("domain", help="Domain operations")
    domain_sub = domain_parser.add_subparsers(dest="subcommand")

    # domain create
    domain_create = domain_sub.add_parser("create", help="Create domain for compose service")
    domain_create.add_argument("compose_id", help="Compose service ID")
    domain_create.add_argument("host", help="Full hostname (e.g., cal.arisegroup-tools.com)")
    domain_create.add_argument("port", help="Internal container port")
    domain_create.add_argument("service_name", help="Service name from docker-compose.yml")
    domain_create.add_argument("--path", default="/", help="URL path (default: /)")

    # domain list
    domain_list = domain_sub.add_parser("list", help="List domains for compose service")
    domain_list.add_argument("compose_id", help="Compose service ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        client = DokployClient()

        if args.command == "compose":
            if args.subcommand == "create":
                cmd_compose_create(args, client)
            elif args.subcommand == "update":
                cmd_compose_update(args, client)
            elif args.subcommand == "deploy":
                cmd_compose_deploy(args, client)
            elif args.subcommand == "get":
                cmd_compose_get(args, client)
            elif args.subcommand == "delete":
                cmd_compose_delete(args, client)
            elif args.subcommand == "start":
                client.start_compose(args.compose_id)
                print(f"Started compose service: {args.compose_id}")
            elif args.subcommand == "stop":
                client.stop_compose(args.compose_id)
                print(f"Stopped compose service: {args.compose_id}")
            else:
                compose_parser.print_help()

        elif args.command == "project":
            if args.subcommand == "list":
                cmd_project_list(args, client)
            elif args.subcommand == "get":
                cmd_project_get(args, client)
            else:
                project_parser.print_help()

        elif args.command == "domain":
            if args.subcommand == "create":
                cmd_domain_create(args, client)
            elif args.subcommand == "list":
                cmd_domain_list(args, client)
            else:
                domain_parser.print_help()

    except DokployAuthError as e:
        print(f"Authentication error: {e}", file=sys.stderr)
        sys.exit(1)
    except DokployNotFoundError as e:
        print(f"Not found: {e}", file=sys.stderr)
        sys.exit(1)
    except DokployError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

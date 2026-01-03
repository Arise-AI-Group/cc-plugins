#!/usr/bin/env python3
"""
Demo Deploy Tool

Deploy demo applications to Dokploy with GitHub integration and Traefik routing.
Extends the infrastructure module's DokployClient with demo-specific operations.

Usage (CLI):
    ./run tool/demo_deploy.py list
    ./run tool/demo_deploy.py check <slug>
    ./run tool/demo_deploy.py validate [compose-file]
    ./run tool/demo_deploy.py deploy --name <name> --repo <owner/repo> ...
    ./run tool/demo_deploy.py update <compose-id> --repo <owner/repo>
    ./run tool/demo_deploy.py redeploy <compose-id>

Usage (Module):
    from tool.demo_deploy import DemoDeployClient
    client = DemoDeployClient()
    projects = client.list_projects()
    client.deploy_demo(env_id, "my-demo", "owner/repo", subdomain="my-demo", port=3000)
"""

import sys
import os
import json
import argparse
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List

from .config import get_api_key

# Import DokployClient - requires infrastructure plugin to be installed
try:
    from infrastructure.tool.dokploy_api import DokployClient, DokployError
except ImportError:
    # Fallback for standalone operation - define minimal stubs
    class DokployError(Exception):
        pass
    DokployClient = None

# Load BASE_DOMAIN from env var with fallback
BASE_DOMAIN = get_api_key("BASE_DOMAIN", "arisegroup-tools.com")


class DemoDeployClient:
    """Extended Dokploy client with demo deployment capabilities."""

    def __init__(self):
        self.dokploy = DokployClient()

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Proxy to internal DokployClient._request."""
        return self.dokploy._request(method, endpoint, data)

    # === Project/Environment Management ===

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects in Dokploy."""
        return self._request("GET", "/project.all")

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details including environments and services."""
        return self._request("GET", "/project.one", {"projectId": project_id})

    def list_environments(self, project_id: str) -> List[Dict[str, Any]]:
        """List environments within a project."""
        project = self.get_project(project_id)
        return project.get("environments", [])

    def create_project(self, name: str, description: str = None) -> Dict[str, Any]:
        """Create a new project."""
        data = {"name": name}
        if description:
            data["description"] = description
        return self._request("POST", "/project.create", data)

    def create_environment(self, project_id: str, name: str, description: str = None) -> Dict[str, Any]:
        """Create a new environment within a project."""
        data = {
            "projectId": project_id,
            "name": name
        }
        if description:
            data["description"] = description
        return self._request("POST", "/environment.create", data)

    def list_compose_services(self, project_id: str = None) -> List[Dict[str, Any]]:
        """
        List all compose services, optionally filtered by project.
        Returns list of compose services with their details.
        """
        if project_id:
            project = self.get_project(project_id)
            # Collect composes from all environments in this project
            composes = []
            for env in project.get("environments", []):
                composes.extend(env.get("compose", []))
            return composes
        else:
            # List all projects and collect all composes
            projects = self.list_projects()
            all_composes = []
            for project in projects:
                project_detail = self.get_project(project["projectId"])
                for env in project_detail.get("environments", []):
                    for compose in env.get("compose", []):
                        compose["_projectName"] = project.get("name", "unknown")
                        compose["_environmentId"] = env.get("environmentId")
                        all_composes.append(compose)
            return all_composes

    def find_demo_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a compose service by name."""
        composes = self.list_compose_services()
        for compose in composes:
            if compose.get("name", "").lower() == name.lower():
                return compose
            if compose.get("appName", "").lower() == name.lower():
                return compose
        return None

    def find_demo_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Check if a demo with this subdomain already exists by checking domains."""
        hostname = f"{slug}.{BASE_DOMAIN}"
        composes = self.list_compose_services()
        for compose in composes:
            domains = self.list_domains(compose.get("composeId"))
            for domain in domains:
                if domain.get("host", "").lower() == hostname.lower():
                    return compose
        return None

    # === Domain Management ===

    def list_domains(self, compose_id: str) -> List[Dict[str, Any]]:
        """List domains configured for a compose service."""
        try:
            return self._request("GET", "/domain.byComposeId", {"composeId": compose_id})
        except DokployError:
            return []

    def create_domain(
        self,
        compose_id: str,
        subdomain: str,
        port: int,
        service_name: str,
        path: str = "/"
    ) -> Dict[str, Any]:
        """
        Add domain routing for a compose service.

        Args:
            compose_id: ID of the compose service
            subdomain: Subdomain slug (e.g., "acme-demo")
            port: Internal container port
            service_name: Service name from docker-compose.yml
            path: URL path (default: "/")
        """
        hostname = f"{subdomain}.{BASE_DOMAIN}"
        return self._request("POST", "/domain.create", {
            "composeId": compose_id,
            "host": hostname,
            "port": port,
            "serviceName": service_name,
            "domainType": "compose",
            "https": False,  # Cloudflare handles TLS
            "path": path
        })

    def delete_domain(self, domain_id: str) -> bool:
        """Delete a domain."""
        self._request("POST", "/domain.delete", {"domainId": domain_id})
        return True

    # === GitHub Source Configuration ===

    def get_github_provider(self) -> Optional[Dict[str, Any]]:
        """Get the first available GitHub provider ID."""
        # Try to find a compose with GitHub source to get the provider ID
        composes = self.list_compose_services()
        for compose in composes:
            if compose.get("sourceType") == "github" and compose.get("githubId"):
                return {"githubId": compose.get("githubId")}
        return None

    def list_github_providers(self) -> List[Dict[str, Any]]:
        """List all GitHub providers configured in Dokploy."""
        try:
            return self._request("GET", "/github.githubProviders")
        except DokployError:
            return []

    def get_github_repositories(self, github_id: str) -> List[Dict[str, Any]]:
        """Get list of repositories accessible by a GitHub provider."""
        try:
            return self._request("GET", "/github.getGithubRepositories", {"githubId": github_id})
        except DokployError as e:
            return []

    def test_github_connection(self, github_id: str) -> Dict[str, Any]:
        """Test connection to GitHub provider."""
        try:
            return self._request("POST", "/github.testConnection", {"githubId": github_id})
        except DokployError as e:
            return {"error": str(e)}

    def configure_github_source(
        self,
        compose_id: str,
        repository: str,
        branch: str = "main",
        compose_path: str = "docker-compose.yml",
        github_id: str = None
    ) -> Dict[str, Any]:
        """
        Configure a compose service to pull from GitHub.

        Args:
            compose_id: ID of the compose service
            repository: GitHub repository in "owner/repo" format
            branch: Git branch (default: "main")
            compose_path: Path to compose file in repo (default: "docker-compose.yml")
            github_id: Dokploy GitHub provider ID (auto-detected if not provided)
        """
        # Parse owner/repo format
        if "/" in repository:
            owner, repo_name = repository.split("/", 1)
        else:
            raise ValueError("Repository must be in 'owner/repo' format")

        # Auto-detect GitHub provider ID if not provided
        if not github_id:
            provider = self.get_github_provider()
            if provider:
                github_id = provider["githubId"]

        update_data = {
            "composeId": compose_id,
            "sourceType": "github",
            "repository": repo_name,
            "owner": owner,
            "branch": branch,
            "composePath": compose_path
        }

        if github_id:
            update_data["githubId"] = github_id

        # Update the compose with GitHub configuration
        result = self._request("POST", "/compose.update", update_data)

        # Trigger fetchSourceType to actually clone the repository
        # This is what the UI does after saving GitHub settings
        self._request("POST", "/compose.fetchSourceType", {"composeId": compose_id})

        return result

    # === Compose Validation ===

    def validate_compose_file(self, content: str) -> Dict[str, Any]:
        """
        Validate a docker-compose.yml for Traefik compatibility.

        Returns:
            {
                "valid": bool,
                "errors": [...],
                "warnings": [...],
                "services": {...}
            }
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "services": {}
        }

        try:
            compose = yaml.safe_load(content)
        except yaml.YAMLError as e:
            result["valid"] = False
            result["errors"].append(f"Invalid YAML: {e}")
            return result

        if not isinstance(compose, dict):
            result["valid"] = False
            result["errors"].append("Compose file must be a YAML dictionary")
            return result

        # Check for networks section
        networks = compose.get("networks", {})
        has_dokploy_network = False

        for net_name, net_config in networks.items():
            if net_name == "dokploy-network":
                if net_config and net_config.get("external") is True:
                    has_dokploy_network = True
                else:
                    result["errors"].append(
                        "dokploy-network must be declared with 'external: true'"
                    )
                    result["valid"] = False

        if not has_dokploy_network:
            result["errors"].append(
                "Missing 'dokploy-network' in networks section. Add:\n"
                "networks:\n  dokploy-network:\n    external: true"
            )
            result["valid"] = False

        # Check services
        services = compose.get("services", {})
        if not services:
            result["errors"].append("No services defined in compose file")
            result["valid"] = False
            return result

        public_services = []
        internal_services = []

        for svc_name, svc_config in services.items():
            svc_networks = svc_config.get("networks", [])

            # Handle both list and dict network formats
            if isinstance(svc_networks, dict):
                svc_networks = list(svc_networks.keys())

            on_dokploy = "dokploy-network" in svc_networks
            on_internal = "internal" in svc_networks

            result["services"][svc_name] = {
                "networks": svc_networks,
                "on_dokploy_network": on_dokploy,
                "on_internal_network": on_internal
            }

            # Categorize service
            if on_dokploy:
                public_services.append(svc_name)
            else:
                internal_services.append(svc_name)

            # Check for database services that shouldn't be public
            if svc_name in ["postgres", "mysql", "redis", "mongodb", "db", "database"]:
                if on_dokploy:
                    result["warnings"].append(
                        f"Service '{svc_name}' is on dokploy-network. "
                        "Database services should typically only be on 'internal' network."
                    )

        if not public_services:
            result["errors"].append(
                "No services connected to dokploy-network. "
                "At least one service must be on dokploy-network for Traefik routing."
            )
            result["valid"] = False

        # Check for ports mapping (not needed with Traefik)
        for svc_name, svc_config in services.items():
            if svc_config.get("ports") and svc_name in public_services:
                result["warnings"].append(
                    f"Service '{svc_name}' has 'ports:' mapping. "
                    "This is not needed for Traefik routing and can be removed."
                )

        return result

    # === Deployment Operations ===

    def create_demo(
        self,
        environment_id: str,
        name: str,
        description: str = None
    ) -> Dict[str, Any]:
        """Create a new compose service for a demo."""
        return self.dokploy.create_compose(
            environment_id=environment_id,
            name=name,
            description=description
        )

    def deploy_demo(
        self,
        environment_id: str,
        name: str,
        repository: str,
        branch: str = "main",
        compose_path: str = "docker-compose.yml",
        subdomain: str = None,
        port: int = 3000,
        service_name: str = "app"
    ) -> Dict[str, Any]:
        """
        Full deployment workflow: create compose, configure GitHub, add domain, deploy.

        Args:
            environment_id: Dokploy environment ID
            name: Name for the demo
            repository: GitHub repository (owner/repo)
            branch: Git branch
            compose_path: Path to compose file in repo
            subdomain: Subdomain for the demo (defaults to name)
            port: Internal container port
            service_name: Service name from compose file

        Returns:
            Deployment result with compose details and URL
        """
        subdomain = subdomain or name.lower().replace(" ", "-")

        # Step 1: Create compose service
        compose = self.create_demo(environment_id, name)
        compose_id = compose["composeId"]

        try:
            # Step 2: Configure GitHub source
            self.configure_github_source(
                compose_id=compose_id,
                repository=repository,
                branch=branch,
                compose_path=compose_path
            )

            # Step 3: Add domain
            domain = self.create_domain(
                compose_id=compose_id,
                subdomain=subdomain,
                port=port,
                service_name=service_name
            )

            # Step 4: Deploy
            self.dokploy.deploy_compose(compose_id)

            return {
                "success": True,
                "composeId": compose_id,
                "name": name,
                "repository": repository,
                "url": f"https://{subdomain}.{BASE_DOMAIN}",
                "domain": domain
            }

        except Exception as e:
            # Cleanup on failure
            try:
                self.dokploy.delete_compose(compose_id)
            except:
                pass
            raise DokployError(f"Deployment failed: {e}")

    def redeploy_demo(self, compose_id: str) -> Dict[str, Any]:
        """Redeploy an existing demo."""
        return self.dokploy.deploy_compose(compose_id)

    def delete_demo(self, compose_id: str) -> Dict[str, Any]:
        """Delete a demo compose service."""
        return self.dokploy.delete_compose(compose_id)

    def get_compose(self, compose_id: str) -> Dict[str, Any]:
        """Get compose service details including env vars."""
        return self._request("GET", "/compose.one", {"composeId": compose_id})

    def set_env_vars(self, compose_id: str, env_content: str) -> Dict[str, Any]:
        """
        Set environment variables for a compose service.

        Args:
            compose_id: Compose service ID
            env_content: Newline-separated KEY=value pairs
        """
        return self.dokploy.update_compose(compose_id, env=env_content)


# === CLI Interface ===

def cmd_list(args, client: DemoDeployClient):
    """List existing demo deployments."""
    composes = client.list_compose_services()

    if not composes:
        print("No compose services found.")
        return

    print(f"Found {len(composes)} compose service(s):\n")

    for compose in composes:
        name = compose.get("name", "unnamed")
        compose_id = compose.get("composeId", "")
        status = compose.get("composeStatus", "unknown")
        source = compose.get("sourceType", "raw")
        project = compose.get("_projectName", "")

        print(f"  {name}")
        print(f"    ID: {compose_id}")
        print(f"    Status: {status}")
        print(f"    Source: {source}")
        if project:
            print(f"    Project: {project}")

        # Get domains
        domains = client.list_domains(compose_id)
        if domains:
            for domain in domains:
                host = domain.get("host", "")
                port = domain.get("port", "")
                print(f"    URL: https://{host} (port {port})")
        print()


def cmd_check(args, client: DemoDeployClient):
    """Check if a subdomain is available."""
    slug = args.slug.lower().replace(" ", "-")
    hostname = f"{slug}.{BASE_DOMAIN}"

    existing = client.find_demo_by_slug(slug)

    if existing:
        print(f"Subdomain '{slug}' is NOT available.")
        print(f"  Already used by: {existing.get('name', 'unknown')}")
        print(f"  Compose ID: {existing.get('composeId')}")

        # Suggest alternatives
        print(f"\nSuggested alternatives:")
        for suffix in ["-demo", "-dev", "-staging", "2"]:
            alt = f"{slug}{suffix}"
            if not client.find_demo_by_slug(alt):
                print(f"  - {alt}.{BASE_DOMAIN}")
    else:
        print(f"Subdomain '{slug}' is available!")
        print(f"  URL will be: https://{hostname}")


def cmd_validate(args, client: DemoDeployClient):
    """Validate a compose file for Traefik compatibility."""
    filepath = args.file or "docker-compose.yml"

    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(filepath) as f:
        content = f.read()

    result = client.validate_compose_file(content)

    if result["valid"]:
        print("Compose file is valid for Traefik routing.")
    else:
        print("Compose file has issues:\n")

    if result["errors"]:
        print("ERRORS:")
        for error in result["errors"]:
            print(f"  - {error}")
        print()

    if result["warnings"]:
        print("WARNINGS:")
        for warning in result["warnings"]:
            print(f"  - {warning}")
        print()

    if result["services"]:
        print("SERVICES:")
        for svc_name, svc_info in result["services"].items():
            networks = ", ".join(svc_info["networks"]) or "(none)"
            print(f"  {svc_name}: {networks}")

    sys.exit(0 if result["valid"] else 1)


def cmd_projects(args, client: DemoDeployClient):
    """List available projects and environments."""
    projects = client.list_projects()

    if not projects:
        print("No projects found.")
        return

    print(f"Found {len(projects)} project(s):\n")

    for project in projects:
        name = project.get("name", "unnamed")
        project_id = project.get("projectId", "")
        print(f"  {name}")
        print(f"    Project ID: {project_id}")

        # Get environments
        try:
            detail = client.get_project(project_id)
            envs = detail.get("environments", [])
            for env in envs:
                env_name = env.get("name", "default")
                env_id = env.get("environmentId", "")
                compose_count = len(env.get("compose", []))
                print(f"    Environment: {env_name} ({env_id})")
                print(f"      Compose services: {compose_count}")
        except:
            pass
        print()


def cmd_deploy(args, client: DemoDeployClient):
    """Deploy a new demo."""
    result = client.deploy_demo(
        environment_id=args.environment,
        name=args.name,
        repository=args.repo,
        branch=args.branch,
        compose_path=args.compose_path,
        subdomain=args.subdomain,
        port=args.port,
        service_name=args.service
    )

    print("Demo deployed successfully!")
    print(f"  Name: {result['name']}")
    print(f"  Compose ID: {result['composeId']}")
    print(f"  Repository: {result['repository']}")
    print(f"  URL: {result['url']}")


def cmd_redeploy(args, client: DemoDeployClient):
    """Redeploy an existing demo."""
    # Try to find by name first
    compose = client.find_demo_by_name(args.name_or_id)
    if compose:
        compose_id = compose["composeId"]
        name = compose.get("name", args.name_or_id)
    else:
        compose_id = args.name_or_id
        name = args.name_or_id

    client.redeploy_demo(compose_id)
    print(f"Redeployed: {name}")
    print(f"  Compose ID: {compose_id}")


def cmd_delete(args, client: DemoDeployClient):
    """Delete a demo with safety checks."""
    # Try to find by name first
    compose = client.find_demo_by_name(args.name_or_id)
    if compose:
        compose_id = compose["composeId"]
        name = compose.get("name", args.name_or_id)
        project_name = compose.get("_projectName", "unknown")
        status = compose.get("composeStatus", "unknown")
    else:
        # Try to get details by ID
        compose_id = args.name_or_id
        name = args.name_or_id
        project_name = "unknown"
        status = "unknown"

    # Get domains for this compose
    try:
        domains = client.list_domains(compose_id)
        urls = [f"https://{d.get('host')}" for d in domains if d.get('host')]
    except:
        urls = []

    # Safety checks
    is_production = False
    warnings = []

    # Check for production indicators
    if "prod" in name.lower() or "prod" in project_name.lower():
        is_production = True
        warnings.append("Name contains 'prod' - may be a production service!")

    if status == "done":
        warnings.append("Service is currently running")

    if any("prod" in url.lower() for url in urls):
        is_production = True
        warnings.append("URL contains 'prod' - may be production!")

    # Display what will be deleted
    print(f"\n{'='*50}")
    print(f"DELETE: {name}")
    print(f"{'='*50}")
    print(f"  Compose ID: {compose_id}")
    print(f"  Project: {project_name}")
    print(f"  Status: {status}")
    if urls:
        print(f"  URLs: {', '.join(urls)}")

    if warnings:
        print(f"\n⚠️  WARNINGS:")
        for w in warnings:
            print(f"  - {w}")

    if is_production:
        print(f"\n🚨 THIS APPEARS TO BE A PRODUCTION SERVICE!")

    print()

    if not args.yes:
        if is_production:
            confirm = input(f"Type the full name '{name}' to confirm deletion: ")
            if confirm != name:
                print("Cancelled - name did not match.")
                return
        else:
            confirm = input(f"Delete this service? [y/N] ")
            if confirm.lower() != 'y':
                print("Cancelled.")
                return

    client.delete_demo(compose_id)
    print(f"\n✓ Deleted: {name}")


def cmd_env(args, client: DemoDeployClient):
    """Manage environment variables for a demo."""
    # Find the compose service
    compose = client.find_demo_by_name(args.name_or_id)
    if compose:
        compose_id = compose["composeId"]
        name = compose.get("name", args.name_or_id)
    else:
        compose_id = args.name_or_id
        name = args.name_or_id

    # Get current compose details
    try:
        details = client.get_compose(compose_id)
        current_env = details.get("env", "")
    except:
        current_env = ""

    # If --show, display current env vars
    if args.show:
        print(f"Environment variables for '{name}':\n")
        if current_env:
            # Mask sensitive values
            for line in current_env.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    if any(s in key.upper() for s in ["SECRET", "KEY", "PASSWORD", "TOKEN", "API"]):
                        print(f"  {key}=***masked***")
                    else:
                        print(f"  {key}={value}")
                else:
                    print(f"  {line}")
        else:
            print("  (no environment variables set)")
        return

    # If --file, read env vars from file and push to Dokploy
    if args.file:
        env_file = args.file
        if not os.path.exists(env_file):
            print(f"Error: File not found: {env_file}", file=sys.stderr)
            sys.exit(1)

        with open(env_file) as f:
            new_env = f.read()

        # Filter out comments and empty lines for display
        env_lines = [l for l in new_env.strip().split("\n") if l and not l.startswith("#")]

        print(f"Setting environment variables for '{name}':\n")
        for line in env_lines:
            if "=" in line:
                key, value = line.split("=", 1)
                if any(s in key.upper() for s in ["SECRET", "KEY", "PASSWORD", "TOKEN", "API"]):
                    print(f"  {key}=***masked***")
                else:
                    print(f"  {key}={value[:50]}{'...' if len(value) > 50 else ''}")

        print()

        if not args.yes:
            confirm = input("Push these environment variables to Dokploy? [y/N] ")
            if confirm.lower() != 'y':
                print("Cancelled.")
                return

        client.set_env_vars(compose_id, new_env)
        print(f"✓ Environment variables updated for '{name}'")

        if not args.no_redeploy:
            print("Redeploying to apply changes...")
            client.redeploy_demo(compose_id)
            print(f"✓ Redeployed '{name}'")
        else:
            print("Note: Run 'redeploy' to apply the changes.")
        return

    # If --set, set a single env var
    if args.set:
        if "=" not in args.set:
            print("Error: --set requires KEY=value format", file=sys.stderr)
            sys.exit(1)

        key, value = args.set.split("=", 1)

        # Merge with existing
        env_dict = {}
        if current_env:
            for line in current_env.strip().split("\n"):
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env_dict[k] = v

        env_dict[key] = value
        new_env = "\n".join(f"{k}={v}" for k, v in env_dict.items())

        client.set_env_vars(compose_id, new_env)
        print(f"✓ Set {key} for '{name}'")

        if not args.no_redeploy:
            print("Redeploying to apply changes...")
            client.redeploy_demo(compose_id)
            print(f"✓ Redeployed '{name}'")
        return

    # Default: show help
    print("Usage:")
    print("  env <name> --show              Show current env vars")
    print("  env <name> --file .env         Push env vars from file")
    print("  env <name> --set KEY=value     Set a single env var")


def cmd_create_env(args, client: DemoDeployClient):
    """Create a new project (Dokploy auto-creates a 'production' environment)."""
    if not args.project_name:
        print("Error: --project-name is required", file=sys.stderr)
        sys.exit(1)

    # Create the project (Dokploy automatically creates a 'production' environment)
    result = client.create_project(args.project_name, args.description)

    # Response format: {"project": {...}, "environment": {...}}
    project = result.get("project", {})
    env = result.get("environment", {})

    project_id = project.get("projectId")
    project_name = project.get("name", args.project_name)
    env_id = env.get("environmentId")
    env_name = env.get("name", "production")

    print(f"Created project: {project_name}")
    print(f"  Project ID: {project_id}")
    print(f"  Environment: {env_name} ({env_id})")
    print(f"\nUse this environment ID for deployments:")
    print(f"  ./run modules/demo-deploy/tool/demo_deploy.py deploy -e {env_id} ...")


def cmd_github_debug(args, client: DemoDeployClient):
    """Debug GitHub provider configuration and repository access."""
    print("GitHub Provider Diagnostics")
    print("=" * 50)

    # List all GitHub providers
    providers = client.list_github_providers()
    if not providers:
        print("\nNo GitHub providers found!")
        print("Go to Dokploy UI → Settings → Git Providers to add one.")
        return

    print(f"\nFound {len(providers)} GitHub provider(s):\n")

    for provider in providers:
        github_id = provider.get("githubId", "")
        app_name = provider.get("githubAppName", "unknown")
        installation_id = provider.get("githubInstallationId", "")

        print(f"Provider: {app_name}")
        print(f"  GitHub ID: {github_id}")
        print(f"  Installation ID: {installation_id}")

        # Test connection
        print(f"  Testing connection...", end=" ")
        test_result = client.test_github_connection(github_id)
        if "error" in test_result:
            print(f"FAILED: {test_result['error']}")
        else:
            print("OK")

        # List accessible repositories
        if args.list_repos:
            print(f"  Accessible repositories:")
            repos = client.get_github_repositories(github_id)
            if repos:
                for repo in repos[:20]:  # Limit to first 20
                    repo_name = repo.get("full_name", repo.get("name", "unknown"))
                    private = repo.get("private", False)
                    visibility = "(private)" if private else "(public)"
                    print(f"    - {repo_name} {visibility}")
                if len(repos) > 20:
                    print(f"    ... and {len(repos) - 20} more")

                # Check for specific repo if provided
                if args.check_repo:
                    found = False
                    for repo in repos:
                        full_name = repo.get("full_name", "")
                        if full_name.lower() == args.check_repo.lower():
                            found = True
                            break
                    if found:
                        print(f"\n  ✓ Repository '{args.check_repo}' IS accessible")
                    else:
                        print(f"\n  ✗ Repository '{args.check_repo}' NOT found in accessible repos")
                        print(f"    This means the GitHub App doesn't have access to this repo.")
                        print(f"    Go to GitHub → Settings → Applications → Configure the Dokploy app")
                        print(f"    and add the repository to the access list.")
            else:
                print(f"    (none or error fetching)")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Deploy demo applications to Dokploy with GitHub integration"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # list
    subparsers.add_parser("list", help="List existing demo deployments")

    # projects
    subparsers.add_parser("projects", help="List available projects and environments")

    # check
    check_parser = subparsers.add_parser("check", help="Check if subdomain is available")
    check_parser.add_argument("slug", help="Subdomain slug to check")

    # validate
    validate_parser = subparsers.add_parser("validate", help="Validate compose file")
    validate_parser.add_argument("file", nargs="?", help="Path to compose file (default: docker-compose.yml)")

    # deploy
    deploy_parser = subparsers.add_parser("deploy", help="Deploy a new demo")
    deploy_parser.add_argument("--environment", "-e", required=True, help="Dokploy environment ID")
    deploy_parser.add_argument("--name", "-n", required=True, help="Name for the demo")
    deploy_parser.add_argument("--repo", "-r", required=True, help="GitHub repository (owner/repo)")
    deploy_parser.add_argument("--branch", "-b", default="main", help="Git branch (default: main)")
    deploy_parser.add_argument("--compose-path", default="docker-compose.yml", help="Path to compose file")
    deploy_parser.add_argument("--subdomain", "-s", help="Subdomain (defaults to name)")
    deploy_parser.add_argument("--port", "-p", type=int, default=3000, help="Internal port (default: 3000)")
    deploy_parser.add_argument("--service", default="app", help="Service name from compose (default: app)")

    # redeploy
    redeploy_parser = subparsers.add_parser("redeploy", help="Redeploy an existing demo")
    redeploy_parser.add_argument("name_or_id", help="Demo name or compose ID")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete a demo")
    delete_parser.add_argument("name_or_id", help="Demo name or compose ID")
    delete_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    # create-env
    create_env_parser = subparsers.add_parser("create-env", help="Create a new project with environment")
    create_env_parser.add_argument("--project-name", "-n", required=True, help="Name for new project")
    create_env_parser.add_argument("--description", "-d", help="Project description")

    # env
    env_parser = subparsers.add_parser("env", help="Manage environment variables")
    env_parser.add_argument("name_or_id", help="Demo name or compose ID")
    env_parser.add_argument("--show", action="store_true", help="Show current env vars")
    env_parser.add_argument("--file", "-f", help="Push env vars from file (e.g., .env)")
    env_parser.add_argument("--set", help="Set a single env var (KEY=value)")
    env_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    env_parser.add_argument("--no-redeploy", action="store_true", help="Don't redeploy after setting")

    # github-debug
    github_debug_parser = subparsers.add_parser("github-debug", help="Debug GitHub provider configuration")
    github_debug_parser.add_argument("--list-repos", "-l", action="store_true", help="List accessible repositories")
    github_debug_parser.add_argument("--check-repo", "-c", help="Check if specific repo is accessible (owner/repo)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        client = DemoDeployClient()

        if args.command == "list":
            cmd_list(args, client)
        elif args.command == "projects":
            cmd_projects(args, client)
        elif args.command == "check":
            cmd_check(args, client)
        elif args.command == "validate":
            cmd_validate(args, client)
        elif args.command == "deploy":
            cmd_deploy(args, client)
        elif args.command == "redeploy":
            cmd_redeploy(args, client)
        elif args.command == "delete":
            cmd_delete(args, client)
        elif args.command == "create-env":
            cmd_create_env(args, client)
        elif args.command == "env":
            cmd_env(args, client)
        elif args.command == "github-debug":
            cmd_github_debug(args, client)
        else:
            parser.print_help()

    except DokployError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Cloudflare API Integration Script

Execution tool for managing Cloudflare DNS records and zones.
Designed for managing subdomains pointing to Cloudflare tunnels.

Usage (CLI):
    ./run tool/cloudflare_api.py zones list
    ./run tool/cloudflare_api.py zones get <zone_name>

    ./run tool/cloudflare_api.py dns list <zone_id_or_name>
    ./run tool/cloudflare_api.py dns create <zone_id_or_name> <subdomain> <target> [--type CNAME] [--proxied]
    ./run tool/cloudflare_api.py dns delete <zone_id_or_name> <record_id>
    ./run tool/cloudflare_api.py dns update <zone_id_or_name> <record_id> --target <new_target>

Usage (Module):
    from tool.cloudflare_api import CloudflareClient
    client = CloudflareClient()
    zones = client.list_zones()
    client.create_dns_record("example.com", "n8n", "tunnel-id.cfargotunnel.com")
"""

import sys
import os
import json
import argparse
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any

from .config import get_api_key

CLOUDFLARE_API_TOKEN = get_api_key("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = get_api_key("CLOUDFLARE_ACCOUNT_ID")

API_BASE = "https://api.cloudflare.com/client/v4"


# --- Custom Exceptions ---

class CloudflareError(Exception):
    """Base exception for Cloudflare API errors."""
    pass


class CloudflareAuthError(CloudflareError):
    """Authentication/token error."""
    pass


class CloudflareNotFoundError(CloudflareError):
    """Zone/record not found."""
    pass


class CloudflareClient:
    """Client for interacting with Cloudflare API."""

    def __init__(self, api_token: str = None, account_id: str = None):
        self.api_token = api_token or CLOUDFLARE_API_TOKEN
        self.account_id = account_id or CLOUDFLARE_ACCOUNT_ID

        if not self.api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN not configured. Set it in .env file.")

        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        self._zone_cache: Dict[str, str] = {}  # name -> id cache

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make an API request to Cloudflare."""
        url = f"{API_BASE}{endpoint}"

        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            json=data
        )

        result = response.json()

        if not result.get("success", False):
            errors = result.get("errors", [])
            error_msg = errors[0].get("message", "Unknown error") if errors else "Unknown error"
            error_code = errors[0].get("code", 0) if errors else 0

            if error_code == 10000 or response.status_code == 401:
                raise CloudflareAuthError(f"Authentication failed: {error_msg}")
            elif response.status_code == 404:
                raise CloudflareNotFoundError(error_msg)
            else:
                raise CloudflareError(f"API error: {error_msg}")

        return result

    # --- Zone Operations ---

    def list_zones(self) -> List[Dict[str, Any]]:
        """List all zones in the account."""
        result = self._request("GET", "/zones")
        zones = result.get("result", [])

        # Update cache
        for zone in zones:
            self._zone_cache[zone["name"]] = zone["id"]

        return zones

    def get_zone(self, zone_name: str) -> Dict[str, Any]:
        """Get zone details by name."""
        result = self._request("GET", f"/zones?name={zone_name}")
        zones = result.get("result", [])

        if not zones:
            raise CloudflareNotFoundError(f"Zone not found: {zone_name}")

        zone = zones[0]
        self._zone_cache[zone["name"]] = zone["id"]
        return zone

    def get_zone_id(self, zone_name_or_id: str) -> str:
        """Resolve a zone name or ID to a zone ID."""
        # If it looks like a zone ID (32 hex chars), return as-is
        if len(zone_name_or_id) == 32 and all(c in '0123456789abcdef' for c in zone_name_or_id.lower()):
            return zone_name_or_id

        # Check cache first
        if zone_name_or_id in self._zone_cache:
            return self._zone_cache[zone_name_or_id]

        # Look up zone
        zone = self.get_zone(zone_name_or_id)
        return zone["id"]

    # --- DNS Record Operations ---

    def list_dns_records(self, zone_name_or_id: str, record_type: str = None) -> List[Dict[str, Any]]:
        """List DNS records for a zone."""
        zone_id = self.get_zone_id(zone_name_or_id)

        endpoint = f"/zones/{zone_id}/dns_records"
        if record_type:
            endpoint += f"?type={record_type}"

        result = self._request("GET", endpoint)
        return result.get("result", [])

    def get_dns_record(self, zone_name_or_id: str, record_id: str) -> Dict[str, Any]:
        """Get a specific DNS record."""
        zone_id = self.get_zone_id(zone_name_or_id)
        result = self._request("GET", f"/zones/{zone_id}/dns_records/{record_id}")
        return result.get("result", {})

    def create_dns_record(
        self,
        zone_name_or_id: str,
        name: str,
        content: str,
        record_type: str = "CNAME",
        proxied: bool = True,
        ttl: int = 1,  # 1 = automatic
        comment: str = None
    ) -> Dict[str, Any]:
        """
        Create a DNS record.

        Args:
            zone_name_or_id: Zone name (e.g., "example.com") or zone ID
            name: Record name (e.g., "n8n" for n8n.example.com)
            content: Record content (e.g., tunnel ID for CNAME)
            record_type: DNS record type (default: CNAME)
            proxied: Whether to proxy through Cloudflare (orange cloud)
            ttl: Time to live (1 = automatic)
            comment: Optional comment for the record

        Returns:
            Created record details
        """
        zone_id = self.get_zone_id(zone_name_or_id)

        data = {
            "type": record_type,
            "name": name,
            "content": content,
            "proxied": proxied,
            "ttl": ttl
        }

        if comment:
            data["comment"] = comment

        result = self._request("POST", f"/zones/{zone_id}/dns_records", data)
        return result.get("result", {})

    def update_dns_record(
        self,
        zone_name_or_id: str,
        record_id: str,
        name: str = None,
        content: str = None,
        record_type: str = None,
        proxied: bool = None,
        ttl: int = None
    ) -> Dict[str, Any]:
        """Update an existing DNS record."""
        zone_id = self.get_zone_id(zone_name_or_id)

        # Get current record to preserve unchanged fields
        current = self.get_dns_record(zone_name_or_id, record_id)

        data = {
            "type": record_type if record_type is not None else current["type"],
            "name": name if name is not None else current["name"],
            "content": content if content is not None else current["content"],
            "proxied": proxied if proxied is not None else current["proxied"],
            "ttl": ttl if ttl is not None else current["ttl"]
        }

        result = self._request("PUT", f"/zones/{zone_id}/dns_records/{record_id}", data)
        return result.get("result", {})

    def delete_dns_record(self, zone_name_or_id: str, record_id: str) -> bool:
        """Delete a DNS record."""
        zone_id = self.get_zone_id(zone_name_or_id)
        self._request("DELETE", f"/zones/{zone_id}/dns_records/{record_id}")
        return True

    def find_dns_record(self, zone_name_or_id: str, name: str, record_type: str = None) -> Optional[Dict[str, Any]]:
        """Find a DNS record by name."""
        records = self.list_dns_records(zone_name_or_id, record_type)

        # Normalize the search name
        zone_id = self.get_zone_id(zone_name_or_id)

        for record in records:
            # Match by exact name or subdomain
            if record["name"] == name or record["name"].startswith(f"{name}."):
                return record

        return None

    # --- Tunnel Operations ---

    def list_tunnels(self) -> List[Dict[str, Any]]:
        """List all tunnels in the account."""
        if not self.account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID required for tunnel operations")
        result = self._request("GET", f"/accounts/{self.account_id}/cfd_tunnel")
        return result.get("result", [])

    def get_tunnel(self, tunnel_id: str) -> Dict[str, Any]:
        """Get tunnel details."""
        if not self.account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID required for tunnel operations")
        result = self._request("GET", f"/accounts/{self.account_id}/cfd_tunnel/{tunnel_id}")
        return result.get("result", {})

    def get_tunnel_config(self, tunnel_id: str) -> Dict[str, Any]:
        """Get tunnel configuration (ingress rules)."""
        if not self.account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID required for tunnel operations")
        result = self._request("GET", f"/accounts/{self.account_id}/cfd_tunnel/{tunnel_id}/configurations")
        return result.get("result", {})

    def update_tunnel_config(self, tunnel_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update tunnel configuration (ingress rules)."""
        if not self.account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID required for tunnel operations")
        result = self._request("PUT", f"/accounts/{self.account_id}/cfd_tunnel/{tunnel_id}/configurations", config)
        return result.get("result", {})

    def add_tunnel_route(
        self,
        tunnel_id: str,
        hostname: str,
        service: str,
        path: str = None
    ) -> Dict[str, Any]:
        """
        Add a route to the tunnel configuration.

        Args:
            tunnel_id: The tunnel ID
            hostname: Public hostname (e.g., "n8n.example.com")
            service: Backend service URL (e.g., "http://localhost:5678")
            path: Optional path prefix

        Returns:
            Updated tunnel configuration
        """
        # Get current config
        current = self.get_tunnel_config(tunnel_id)
        config = current.get("config", {"ingress": []})
        ingress = config.get("ingress", [])

        # Create new ingress rule
        new_rule = {
            "hostname": hostname,
            "service": service
        }
        if path:
            new_rule["path"] = path

        # Remove any existing rule for this hostname
        ingress = [r for r in ingress if r.get("hostname") != hostname]

        # Add new rule before the catch-all (last rule should be catch-all)
        # Find catch-all rule (no hostname)
        catch_all = None
        for i, rule in enumerate(ingress):
            if "hostname" not in rule or rule.get("hostname") is None:
                catch_all = ingress.pop(i)
                break

        ingress.append(new_rule)

        # Re-add catch-all at the end
        if catch_all:
            ingress.append(catch_all)
        else:
            # Add default catch-all if none exists
            ingress.append({"service": "http_status:404"})

        config["ingress"] = ingress
        return self.update_tunnel_config(tunnel_id, {"config": config})

    def remove_tunnel_route(self, tunnel_id: str, hostname: str) -> Dict[str, Any]:
        """Remove a route from the tunnel configuration."""
        current = self.get_tunnel_config(tunnel_id)
        config = current.get("config", {"ingress": []})
        ingress = config.get("ingress", [])

        # Remove rule for this hostname
        ingress = [r for r in ingress if r.get("hostname") != hostname]

        config["ingress"] = ingress
        return self.update_tunnel_config(tunnel_id, {"config": config})


# --- CLI Interface ---

def cmd_zones_list(args, client: CloudflareClient):
    """List all zones."""
    zones = client.list_zones()

    print(f"Found {len(zones)} zone(s):\n")
    for zone in zones:
        status = zone.get("status", "unknown")
        print(f"  {zone['name']}")
        print(f"    ID: {zone['id']}")
        print(f"    Status: {status}")
        print()


def cmd_zones_get(args, client: CloudflareClient):
    """Get zone details."""
    zone = client.get_zone(args.zone_name)
    print(json.dumps(zone, indent=2))


def cmd_dns_list(args, client: CloudflareClient):
    """List DNS records for a zone."""
    records = client.list_dns_records(args.zone, args.type)

    print(f"Found {len(records)} record(s):\n")
    for record in records:
        proxied = "P" if record.get("proxied") else " "
        print(f"  [{proxied}] {record['type']:6} {record['name']}")
        print(f"       -> {record['content']}")
        print(f"       ID: {record['id']}")
        print()


def cmd_dns_create(args, client: CloudflareClient):
    """Create a DNS record."""
    record = client.create_dns_record(
        zone_name_or_id=args.zone,
        name=args.subdomain,
        content=args.target,
        record_type=args.type,
        proxied=args.proxied,
        comment=args.comment
    )

    print(f"Created DNS record:")
    print(f"  Name: {record['name']}")
    print(f"  Type: {record['type']}")
    print(f"  Content: {record['content']}")
    print(f"  Proxied: {record['proxied']}")
    print(f"  ID: {record['id']}")


def cmd_dns_delete(args, client: CloudflareClient):
    """Delete a DNS record."""
    # If record_id looks like a subdomain, try to find the record first
    if not (len(args.record_id) == 32 and all(c in '0123456789abcdef' for c in args.record_id.lower())):
        record = client.find_dns_record(args.zone, args.record_id)
        if record:
            args.record_id = record["id"]
            print(f"Found record: {record['name']} -> {record['content']}")
        else:
            print(f"Record not found: {args.record_id}")
            return

    if not args.yes:
        confirm = input("Are you sure you want to delete this record? [y/N] ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return

    client.delete_dns_record(args.zone, args.record_id)
    print("Record deleted.")


def cmd_dns_update(args, client: CloudflareClient):
    """Update a DNS record."""
    record = client.update_dns_record(
        zone_name_or_id=args.zone,
        record_id=args.record_id,
        content=args.target,
        proxied=args.proxied if hasattr(args, 'proxied') else None
    )

    print(f"Updated DNS record:")
    print(f"  Name: {record['name']}")
    print(f"  Content: {record['content']}")
    print(f"  Proxied: {record['proxied']}")


def main():
    parser = argparse.ArgumentParser(description="Cloudflare API CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command group")

    # --- Zones commands ---
    zones_parser = subparsers.add_parser("zones", help="Zone operations")
    zones_sub = zones_parser.add_subparsers(dest="subcommand")

    zones_sub.add_parser("list", help="List all zones")

    zones_get = zones_sub.add_parser("get", help="Get zone details")
    zones_get.add_argument("zone_name", help="Zone name (e.g., example.com)")

    # --- DNS commands ---
    dns_parser = subparsers.add_parser("dns", help="DNS record operations")
    dns_sub = dns_parser.add_subparsers(dest="subcommand")

    dns_list = dns_sub.add_parser("list", help="List DNS records")
    dns_list.add_argument("zone", help="Zone name or ID")
    dns_list.add_argument("--type", help="Filter by record type (A, CNAME, etc.)")

    dns_create = dns_sub.add_parser("create", help="Create DNS record")
    dns_create.add_argument("zone", help="Zone name or ID")
    dns_create.add_argument("subdomain", help="Subdomain name (e.g., 'n8n' for n8n.example.com)")
    dns_create.add_argument("target", help="Target content (e.g., tunnel ID for CNAME)")
    dns_create.add_argument("--type", default="CNAME", help="Record type (default: CNAME)")
    dns_create.add_argument("--proxied", action="store_true", default=True, help="Proxy through Cloudflare (default: true)")
    dns_create.add_argument("--no-proxy", action="store_false", dest="proxied", help="Don't proxy through Cloudflare")
    dns_create.add_argument("--comment", help="Comment for the record")

    dns_delete = dns_sub.add_parser("delete", help="Delete DNS record")
    dns_delete.add_argument("zone", help="Zone name or ID")
    dns_delete.add_argument("record_id", help="Record ID or subdomain name")
    dns_delete.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    dns_update = dns_sub.add_parser("update", help="Update DNS record")
    dns_update.add_argument("zone", help="Zone name or ID")
    dns_update.add_argument("record_id", help="Record ID")
    dns_update.add_argument("--target", help="New target content")
    dns_update.add_argument("--proxied", action="store_true", help="Enable proxy")
    dns_update.add_argument("--no-proxy", action="store_false", dest="proxied", help="Disable proxy")

    # --- Tunnel commands ---
    tunnel_parser = subparsers.add_parser("tunnel", help="Tunnel operations")
    tunnel_sub = tunnel_parser.add_subparsers(dest="subcommand")

    tunnel_sub.add_parser("list", help="List all tunnels")

    tunnel_get = tunnel_sub.add_parser("get", help="Get tunnel details")
    tunnel_get.add_argument("tunnel_id", help="Tunnel ID")

    tunnel_config = tunnel_sub.add_parser("config", help="Get tunnel configuration")
    tunnel_config.add_argument("tunnel_id", help="Tunnel ID")

    tunnel_route_add = tunnel_sub.add_parser("route-add", help="Add tunnel route")
    tunnel_route_add.add_argument("tunnel_id", help="Tunnel ID")
    tunnel_route_add.add_argument("hostname", help="Public hostname (e.g., n8n.example.com)")
    tunnel_route_add.add_argument("service", help="Backend service URL (e.g., http://localhost:5678)")
    tunnel_route_add.add_argument("--path", help="Optional path prefix")

    tunnel_route_rm = tunnel_sub.add_parser("route-remove", help="Remove tunnel route")
    tunnel_route_rm.add_argument("tunnel_id", help="Tunnel ID")
    tunnel_route_rm.add_argument("hostname", help="Hostname to remove")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        client = CloudflareClient()

        if args.command == "zones":
            if args.subcommand == "list":
                cmd_zones_list(args, client)
            elif args.subcommand == "get":
                cmd_zones_get(args, client)
            else:
                zones_parser.print_help()

        elif args.command == "dns":
            if args.subcommand == "list":
                cmd_dns_list(args, client)
            elif args.subcommand == "create":
                cmd_dns_create(args, client)
            elif args.subcommand == "delete":
                cmd_dns_delete(args, client)
            elif args.subcommand == "update":
                cmd_dns_update(args, client)
            else:
                dns_parser.print_help()

        elif args.command == "tunnel":
            if args.subcommand == "list":
                tunnels = client.list_tunnels()
                print(f"Found {len(tunnels)} tunnel(s):\n")
                for t in tunnels:
                    status = "OK" if t.get("status") == "healthy" else "ERR"
                    print(f"  [{status}] {t.get('name', 'unnamed')}")
                    print(f"     ID: {t['id']}")
                    print(f"     Status: {t.get('status', 'unknown')}")
                    print()
            elif args.subcommand == "get":
                tunnel = client.get_tunnel(args.tunnel_id)
                print(json.dumps(tunnel, indent=2))
            elif args.subcommand == "config":
                config = client.get_tunnel_config(args.tunnel_id)
                print(json.dumps(config, indent=2))
            elif args.subcommand == "route-add":
                result = client.add_tunnel_route(
                    args.tunnel_id,
                    args.hostname,
                    args.service,
                    args.path
                )
                print(f"Added route: {args.hostname} -> {args.service}")
                print(f"Current ingress rules:")
                for rule in result.get("config", {}).get("ingress", []):
                    hostname = rule.get("hostname", "(catch-all)")
                    service = rule.get("service")
                    print(f"  {hostname} -> {service}")
            elif args.subcommand == "route-remove":
                result = client.remove_tunnel_route(args.tunnel_id, args.hostname)
                print(f"Removed route: {args.hostname}")
            else:
                tunnel_parser.print_help()

    except CloudflareAuthError as e:
        print(f"Authentication error: {e}", file=sys.stderr)
        sys.exit(1)
    except CloudflareNotFoundError as e:
        print(f"Not found: {e}", file=sys.stderr)
        sys.exit(1)
    except CloudflareError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

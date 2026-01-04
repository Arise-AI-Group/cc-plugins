#!/usr/bin/env python3
"""
Emergency cleanup script for orphaned test resources.

Run this script to find and clean up any test resources
that were left behind from failed test runs.

Usage:
    python tests/cleanup_all.py
    python tests/cleanup_all.py --dry-run  # Preview only
"""
import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load credentials
ENV_PATH = Path.home() / ".config" / "cc-plugins" / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

TEST_PREFIX = "test-ccplugins-"


def cleanup_slack(dry_run: bool = False):
    """Clean up orphaned Slack test resources."""
    print("\n=== Cleaning up Slack resources ===")

    if not os.getenv("SLACK_BOT_TOKEN"):
        print("  Skipping: SLACK_BOT_TOKEN not configured")
        return

    try:
        from slack.tool.slack_api import SlackClient
        client = SlackClient()

        # Find test channels
        channels = client.list_channels(limit=200)
        test_channels = [
            ch for ch in channels
            if ch.get("name", "").startswith(TEST_PREFIX)
            and not ch.get("is_archived")
        ]

        if not test_channels:
            print("  No orphaned test channels found")
            return

        print(f"  Found {len(test_channels)} test channel(s):")
        for ch in test_channels:
            print(f"    - {ch['name']} ({ch['id']})")
            if not dry_run:
                try:
                    client.archive_channel(ch["id"])
                    print(f"      Archived")
                except Exception as e:
                    print(f"      Failed: {e}")

    except ImportError:
        print("  Skipping: Slack module not available")
    except Exception as e:
        print(f"  Error: {e}")


def cleanup_notion(dry_run: bool = False):
    """Clean up orphaned Notion test resources."""
    print("\n=== Cleaning up Notion resources ===")

    if not os.getenv("NOTION_API_KEY"):
        print("  Skipping: NOTION_API_KEY not configured")
        return

    try:
        from notion.tool.notion_api import NotionClient
        client = NotionClient()

        # Search for test pages
        results = client.search(query=TEST_PREFIX)
        test_pages = [
            r for r in results.get("results", [])
            if r.get("object") == "page"
            and not r.get("archived")
        ]

        if not test_pages:
            print("  No orphaned test pages found")
            return

        print(f"  Found {len(test_pages)} test page(s):")
        for page in test_pages:
            page_id = page["id"]
            print(f"    - {page_id}")
            if not dry_run:
                try:
                    client.archive_page(page_id)
                    print(f"      Archived")
                except Exception as e:
                    print(f"      Failed: {e}")

    except ImportError:
        print("  Skipping: Notion module not available")
    except Exception as e:
        print(f"  Error: {e}")


def cleanup_n8n(dry_run: bool = False):
    """Clean up orphaned n8n test resources."""
    print("\n=== Cleaning up n8n resources ===")

    if not os.getenv("N8N_API_KEY"):
        print("  Skipping: N8N_API_KEY not configured")
        return

    try:
        from n8n.tool.n8n_api import N8nClient
        client = N8nClient()

        # List all workflows
        workflows = client.list_workflows()
        test_workflows = [
            wf for wf in workflows
            if wf.get("name", "").startswith(TEST_PREFIX)
        ]

        if not test_workflows:
            print("  No orphaned test workflows found")
            return

        print(f"  Found {len(test_workflows)} test workflow(s):")
        for wf in test_workflows:
            print(f"    - {wf['name']} ({wf['id']})")
            if not dry_run:
                try:
                    client.deactivate_workflow(wf["id"])
                    client.delete_workflow(wf["id"])
                    print(f"      Deleted")
                except Exception as e:
                    print(f"      Failed: {e}")

    except ImportError:
        print("  Skipping: n8n module not available")
    except Exception as e:
        print(f"  Error: {e}")


def cleanup_cloudflare(dry_run: bool = False):
    """Clean up orphaned Cloudflare test resources."""
    print("\n=== Cleaning up Cloudflare resources ===")

    if not os.getenv("CLOUDFLARE_API_TOKEN"):
        print("  Skipping: CLOUDFLARE_API_TOKEN not configured")
        return

    try:
        from infrastructure.tool.cloudflare_api import CloudflareClient
        client = CloudflareClient()

        # Check each zone for test DNS records
        zones = client.list_zones()
        total_deleted = 0

        for zone in zones:
            records = client.list_dns_records(zone["id"])
            test_records = [
                r for r in records
                if TEST_PREFIX in r.get("name", "")
            ]

            if test_records:
                print(f"  Zone {zone['name']}:")
                for record in test_records:
                    print(f"    - {record['name']} ({record['type']})")
                    if not dry_run:
                        try:
                            client.delete_dns_record(zone["id"], record["id"])
                            print(f"      Deleted")
                            total_deleted += 1
                        except Exception as e:
                            print(f"      Failed: {e}")

        if total_deleted == 0 and not any(
            TEST_PREFIX in r.get("name", "")
            for zone in zones
            for r in client.list_dns_records(zone["id"])
        ):
            print("  No orphaned test DNS records found")

    except ImportError:
        print("  Skipping: Cloudflare module not available")
    except Exception as e:
        print(f"  Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Clean up orphaned test resources"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be cleaned up without making changes"
    )
    args = parser.parse_args()

    if args.dry_run:
        print("=== DRY RUN MODE - No changes will be made ===")

    print(f"Looking for resources with prefix: {TEST_PREFIX}")

    cleanup_slack(args.dry_run)
    cleanup_notion(args.dry_run)
    cleanup_n8n(args.dry_run)
    cleanup_cloudflare(args.dry_run)

    print("\n=== Cleanup complete ===")


if __name__ == "__main__":
    main()

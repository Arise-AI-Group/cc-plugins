#!/usr/bin/env python3
"""
Huddle Sync Tool - Sync Slack Huddles to Notion Meetings Database

Features:
- Dynamic user mapping (Slack -> Notion by email)
- Dynamic channel name discovery
- Database auto-discovery (searches for "Meetings" database)
- Local caching for fast subsequent runs

Usage:
    ./run tool/huddle_sync.py sync          # Create new pages for all huddles
    ./run tool/huddle_sync.py update        # Update existing huddle pages
    ./run tool/huddle_sync.py refresh       # Rebuild mappings cache
    ./run tool/huddle_sync.py status        # Show cache status

Cache location: ~/.config/cc-plugins/cache/huddle_mappings.json
"""

import subprocess
import json
import re
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .config import get_api_key

# Cache settings
CACHE_DIR = Path.home() / ".config" / "cc-plugins" / "cache"
CACHE_FILE = CACHE_DIR / "huddle_mappings.json"
CACHE_MAX_AGE_DAYS = 7

# Notion API limits
MAX_RICH_TEXT_LENGTH = 1900


class HuddleSyncClient:
    """Client for syncing Slack huddles to Notion."""

    def __init__(self):
        self._cache = None
        self._slack_dir = self._find_plugin_dir("slack")
        self._notion_dir = self._find_plugin_dir("notion")

    def _find_plugin_dir(self, plugin_name: str) -> Path:
        """Find plugin directory - works for both cloned and cached installations."""
        # First check if we're in a cloned repo (sibling directories)
        tool_dir = Path(__file__).parent
        plugin_dir = tool_dir.parent  # notion/
        repo_root = plugin_dir.parent  # cc-plugins/
        sibling = repo_root / plugin_name
        if sibling.exists() and (sibling / "tool").exists():
            return sibling

        # Check Claude Code plugin cache
        cache_base = Path.home() / ".claude" / "plugins" / "cache"
        if cache_base.exists():
            # Look for cc-plugins marketplace
            for marketplace in cache_base.iterdir():
                if not marketplace.is_dir():
                    continue
                plugin_path = marketplace / plugin_name
                if plugin_path.exists():
                    # Find latest version
                    versions = [v for v in plugin_path.iterdir() if v.is_dir()]
                    if versions:
                        latest = sorted(versions, key=lambda x: x.name)[-1]
                        if (latest / "tool").exists():
                            return latest

        raise RuntimeError(f"Could not find {plugin_name} plugin. Is it installed?")

    def _run_slack_cmd(self, args: list[str]) -> str:
        """Run a Slack CLI command."""
        cmd = ["./run", "tool/slack_api.py"] + args
        result = subprocess.run(cmd, cwd=self._slack_dir, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Slack command failed: {result.stderr}")
        return result.stdout

    def _run_notion_cmd(self, args: list[str]) -> str:
        """Run a Notion CLI command."""
        cmd = ["./run", "tool/notion_api.py"] + args
        result = subprocess.run(cmd, cwd=self._notion_dir, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Notion command failed: {result.stderr}")
        return result.stdout

    def _parse_json_output(self, output: str) -> dict | list:
        """Parse JSON from CLI output (skip header lines)."""
        lines = output.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('{') or stripped.startswith('['):
                return json.loads('\n'.join(lines[i:]))
        return {}

    # === Cache Management ===

    def _load_cache(self) -> dict:
        """Load mappings from cache file."""
        if self._cache is not None:
            return self._cache

        if CACHE_FILE.exists():
            try:
                self._cache = json.loads(CACHE_FILE.read_text())
                return self._cache
            except Exception:
                pass

        self._cache = {}
        return self._cache

    def _save_cache(self, cache: dict):
        """Save mappings to cache file."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache["updated_at"] = datetime.now().isoformat()
        CACHE_FILE.write_text(json.dumps(cache, indent=2))
        self._cache = cache

    def _is_cache_stale(self) -> bool:
        """Check if cache is older than max age."""
        cache = self._load_cache()
        if not cache.get("updated_at"):
            return True
        try:
            updated = datetime.fromisoformat(cache["updated_at"])
            return datetime.now() - updated > timedelta(days=CACHE_MAX_AGE_DAYS)
        except Exception:
            return True

    # === Dynamic Discovery ===

    def _discover_slack_users(self) -> dict[str, dict]:
        """Get all Slack users with email info."""
        print("  Fetching Slack users...")
        output = self._run_slack_cmd(["users", "list"])
        users = self._parse_json_output(output)
        return {u["id"]: u for u in users if not u.get("is_bot") and not u.get("deleted")}

    def _discover_notion_users(self) -> dict[str, dict]:
        """Get all Notion users."""
        print("  Fetching Notion users...")
        output = self._run_notion_cmd(["users", "list"])
        users = self._parse_json_output(output)
        return {u["id"]: u for u in users if u.get("type") == "person"}

    def _build_user_mapping(self, slack_users: dict, notion_users: dict) -> dict[str, str]:
        """Build Slack ID -> Notion ID mapping by email."""
        print("  Building user mapping by email...")
        mapping = {}

        # Build email -> Notion ID lookup
        notion_by_email = {}
        for uid, user in notion_users.items():
            email = user.get("person", {}).get("email", "").lower()
            if email:
                notion_by_email[email] = uid

        # Match Slack users to Notion by email
        for slack_id, slack_user in slack_users.items():
            profile = slack_user.get("profile", {})
            email = profile.get("email", "").lower()
            if email and email in notion_by_email:
                mapping[slack_id] = notion_by_email[email]
                name = profile.get("real_name", slack_id)
                print(f"    Matched: {name}")

        return mapping

    def _discover_channels(self) -> dict[str, str]:
        """Get channel ID -> name mapping."""
        print("  Fetching Slack channels...")
        output = self._run_slack_cmd(["channels", "list", "--type", "all"])
        channels = self._parse_json_output(output)
        return {c["id"]: c["name"] for c in channels}

    def _discover_meetings_database(self) -> Optional[str]:
        """Find the Meetings database in Notion."""
        print("  Searching for Meetings database...")
        output = self._run_notion_cmd(["search", "Meetings", "--filter", "database"])
        results = self._parse_json_output(output)

        for item in results:
            if item.get("object") == "database":
                title = item.get("title", [{}])[0].get("plain_text", "")
                if "meeting" in title.lower():
                    print(f"    Found: {title}")
                    return item["id"]

        return None

    def refresh_cache(self) -> dict:
        """Rebuild all mappings from scratch."""
        print("\nRefreshing mappings cache...")

        slack_users = self._discover_slack_users()
        notion_users = self._discover_notion_users()
        user_mapping = self._build_user_mapping(slack_users, notion_users)
        channel_mapping = self._discover_channels()
        database_id = self._discover_meetings_database()

        cache = {
            "user_mapping": user_mapping,
            "channel_mapping": channel_mapping,
            "meetings_database_id": database_id,
        }

        self._save_cache(cache)
        print(f"\nCache updated:")
        print(f"  Users mapped: {len(user_mapping)}")
        print(f"  Channels: {len(channel_mapping)}")
        print(f"  Database: {database_id or 'NOT FOUND'}")

        return cache

    def get_mappings(self) -> dict:
        """Get mappings, refreshing if stale."""
        if self._is_cache_stale():
            return self.refresh_cache()
        return self._load_cache()

    # === Huddle Operations ===

    def get_huddles(self) -> dict:
        """Fetch all huddles from Slack."""
        output = self._run_slack_cmd(["huddles", "find-all"])
        return self._parse_json_output(output)

    def get_notes_content(self, notes_file_id: str) -> str:
        """Get huddle notes content."""
        try:
            output = self._run_slack_cmd(["huddles", "notes", notes_file_id])
            data = json.loads(output)
            return data.get("text", "")
        except Exception as e:
            print(f"    Warning: Could not get notes: {e}")
            return ""

    def get_channel_name(self, channel_id: str) -> str:
        """Get channel name from ID."""
        mappings = self.get_mappings()
        return mappings.get("channel_mapping", {}).get(channel_id, channel_id)

    def map_participants(self, slack_user_ids: list[str]) -> list[dict]:
        """Map Slack user IDs to Notion user references."""
        mappings = self.get_mappings()
        user_mapping = mappings.get("user_mapping", {})
        return [
            {"object": "user", "id": user_mapping[sid]}
            for sid in slack_user_ids
            if sid in user_mapping
        ]

    @staticmethod
    def format_date(timestamp: int) -> str:
        """Convert Unix timestamp to ISO date."""
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

    @staticmethod
    def format_duration(seconds: int) -> int:
        """Convert seconds to minutes."""
        return round(seconds / 60)

    @staticmethod
    def chunk_text(text: str, max_length: int = MAX_RICH_TEXT_LENGTH) -> list[str]:
        """Split text into chunks."""
        if not text:
            return []
        chunks = []
        while text:
            if len(text) <= max_length:
                chunks.append(text)
                break
            break_point = text.rfind('\n', 0, max_length)
            if break_point == -1:
                break_point = text.rfind(' ', 0, max_length)
            if break_point == -1:
                break_point = max_length
            chunks.append(text[:break_point])
            text = text[break_point:].lstrip()
        return chunks

    # === Sync Operations ===

    def sync_new_huddles(self):
        """Create Notion pages for new huddles."""
        mappings = self.get_mappings()
        database_id = mappings.get("meetings_database_id")

        if not database_id:
            print("ERROR: Meetings database not found. Run 'refresh' and check Notion.")
            return

        print("\n" + "=" * 60)
        print("Sync New Huddles to Notion")
        print("=" * 60)

        print("\nFetching huddles from Slack...")
        huddles_by_channel = self.get_huddles()
        total = sum(len(h) for h in huddles_by_channel.values())
        print(f"Found {total} huddles")

        created = 0
        errors = 0

        for channel_id, huddles in huddles_by_channel.items():
            channel_name = self.get_channel_name(channel_id)
            print(f"\n#{channel_name} ({len(huddles)} huddles)")

            for huddle in huddles:
                date_str = self.format_date(huddle["date_start"])
                title = f"#{channel_name} Huddle - {date_str}"
                print(f"  - {title}...")

                try:
                    # Get notes
                    notes_content = ""
                    notes_obj = huddle.get("notes")
                    if notes_obj and isinstance(notes_obj, dict):
                        file_id = notes_obj.get("file_id")
                        if file_id:
                            notes_content = self.get_notes_content(file_id)

                    # Create page
                    page_id = self._create_huddle_page(
                        database_id, title, huddle, notes_content
                    )
                    print(f"    Created: https://notion.so/{page_id.replace('-', '')}")
                    created += 1

                except Exception as e:
                    print(f"    Error: {e}")
                    errors += 1

        print("\n" + "=" * 60)
        print(f"Sync Complete! Created: {created}, Errors: {errors}")

    def _create_huddle_page(self, database_id: str, title: str, huddle: dict, content: str) -> str:
        """Create a Notion page for a huddle."""
        # Write content to temp file
        temp_file = Path(__file__).parent / ".tmp_content.md"
        temp_file.write_text(content or "No notes available.")

        try:
            # Create page
            output = self._run_notion_cmd([
                "pages", "create", database_id,
                "--title", title,
                "--database",
                "--content-file", str(temp_file)
            ])

            # Extract page ID
            match = re.search(r'"id":\s*"([^"]+)"', output)
            if not match:
                raise Exception("Could not parse page ID from response")

            page_id = match.group(1)

            # Update properties
            self._update_huddle_properties(page_id, huddle)

            return page_id

        finally:
            if temp_file.exists():
                temp_file.unlink()

    def _update_huddle_properties(self, page_id: str, huddle: dict):
        """Update page properties."""
        duration = self.format_duration(huddle["duration_seconds"])
        date_str = self.format_date(huddle["date_start"])

        # Get permalink (prefer notes link)
        notes_obj = huddle.get("notes", {})
        url = ""
        if isinstance(notes_obj, dict):
            url = notes_obj.get("permalink", "")
        if not url:
            url = huddle.get("permalink", "")

        properties = {
            "Date": {"date": {"start": date_str}},
            "Duration": {"number": duration},
            "Status": {"select": {"name": "Completed"}},
            "Type": {"select": {"name": "Huddle"}},
            "Source": {"select": {"name": "Slack"}},
        }

        if url:
            properties["External URL"] = {"url": url}

        attendees = self.map_participants(huddle.get("participant_history", []))
        if attendees:
            properties["Team Attendees"] = {"people": attendees}

        try:
            self._run_notion_cmd([
                "pages", "update", page_id,
                "--properties", json.dumps(properties)
            ])
        except Exception as e:
            print(f"    Warning: Could not update properties: {e}")

    def update_existing_huddles(self):
        """Update existing Notion huddle pages with latest content."""
        print("\n" + "=" * 60)
        print("Update Existing Huddle Pages")
        print("=" * 60)

        print("\nFetching huddles from Slack...")
        huddles_by_channel = self.get_huddles()
        huddles_flat = []
        for huddles in huddles_by_channel.values():
            huddles_flat.extend(huddles)
        print(f"Found {len(huddles_flat)} huddles")

        print("\nFetching existing Notion pages...")
        output = self._run_notion_cmd(["search", "Huddle", "--limit", "100"])
        pages = [p for p in self._parse_json_output(output) if p.get("object") == "page"]
        print(f"Found {len(pages)} Huddle pages")

        updated = 0
        skipped = 0

        for page in pages:
            page_id = page["id"]
            title_prop = page.get("properties", {}).get("Name", {}).get("title", [])
            title = title_prop[0].get("plain_text", "") if title_prop else "Unknown"

            print(f"\n{title}")

            # Match to huddle
            huddle = self._match_page_to_huddle(title, huddles_flat)
            if not huddle:
                print("  Skipped: No matching huddle")
                skipped += 1
                continue

            # Get notes
            notes_content = ""
            notes_obj = huddle.get("notes")
            if notes_obj and isinstance(notes_obj, dict):
                file_id = notes_obj.get("file_id")
                if file_id:
                    notes_content = self.get_notes_content(file_id)

            # Update properties
            print("  Updating properties...")
            self._update_huddle_properties(page_id, huddle)

            # Update content
            if notes_content:
                print("  Updating content...")
                self._update_page_content(page_id, notes_content)

            updated += 1

        print("\n" + "=" * 60)
        print(f"Update Complete! Updated: {updated}, Skipped: {skipped}")

    def _match_page_to_huddle(self, title: str, huddles: list[dict]) -> Optional[dict]:
        """Match page title to huddle."""
        match = re.match(r"#(\S+) Huddle - (\d{4}-\d{2}-\d{2})", title)
        if not match:
            return None

        channel_name = match.group(1)
        date_str = match.group(2)

        for huddle in huddles:
            h_channel = self.get_channel_name(huddle["channel_id"])
            h_date = self.format_date(huddle["date_start"])
            if h_channel == channel_name and h_date == date_str:
                return huddle

        return None

    def _update_page_content(self, page_id: str, content: str):
        """Clear and replace page content."""
        # Clear existing blocks
        try:
            output = self._run_notion_cmd(["blocks", "children", page_id])
            blocks = self._parse_json_output(output)
            for block in blocks:
                if block.get("id"):
                    try:
                        self._run_notion_cmd(["blocks", "delete", block["id"]])
                    except Exception:
                        pass
        except Exception:
            pass

        # Add new content in chunks
        for chunk in self.chunk_text(content):
            temp_file = Path(__file__).parent / ".tmp_update.md"
            temp_file.write_text(chunk)
            try:
                self._run_notion_cmd(["blocks", "append", page_id, "--content-file", str(temp_file)])
            finally:
                if temp_file.exists():
                    temp_file.unlink()

    def show_status(self):
        """Show cache status."""
        print("\nHuddle Sync Cache Status")
        print("=" * 40)

        if not CACHE_FILE.exists():
            print("Cache: NOT FOUND")
            print("Run 'refresh' to build mappings")
            return

        cache = self._load_cache()
        updated = cache.get("updated_at", "unknown")
        users = len(cache.get("user_mapping", {}))
        channels = len(cache.get("channel_mapping", {}))
        db = cache.get("meetings_database_id", "NOT SET")

        print(f"Updated: {updated}")
        print(f"Users mapped: {users}")
        print(f"Channels: {channels}")
        print(f"Database ID: {db}")
        print(f"Cache file: {CACHE_FILE}")

        if self._is_cache_stale():
            print("\nWARNING: Cache is stale. Run 'refresh' to update.")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sync Slack Huddles to Notion")
    parser.add_argument(
        "command",
        choices=["sync", "update", "refresh", "status"],
        help="Command to run"
    )

    args = parser.parse_args()

    client = HuddleSyncClient()

    if args.command == "sync":
        client.sync_new_huddles()
    elif args.command == "update":
        client.update_existing_huddles()
    elif args.command == "refresh":
        client.refresh_cache()
    elif args.command == "status":
        client.show_status()


if __name__ == "__main__":
    main()

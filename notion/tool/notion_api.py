#!/usr/bin/env python3
"""
Notion API Integration Script

Execution tool for managing Notion pages, databases, and blocks via the API.
Supports: pages, databases, blocks, search, and users.

Usage (CLI):
    ./run modules/notion/tool/notion_api.py pages get <page_id>
    ./run modules/notion/tool/notion_api.py pages create <parent_id> --title "Title" [--content "Markdown"]
    ./run modules/notion/tool/notion_api.py pages update <page_id> --title "New Title"
    ./run modules/notion/tool/notion_api.py pages archive <page_id>
    ./run modules/notion/tool/notion_api.py pages restore <page_id>

    ./run modules/notion/tool/notion_api.py databases get <database_id>
    ./run modules/notion/tool/notion_api.py databases query <database_id> [--filter JSON] [--sorts JSON]
    ./run modules/notion/tool/notion_api.py databases create <parent_id> --title "Title" --properties JSON

    ./run modules/notion/tool/notion_api.py blocks get <block_id>
    ./run modules/notion/tool/notion_api.py blocks children <block_id> [--as-markdown]
    ./run modules/notion/tool/notion_api.py blocks append <parent_id> --content "Markdown"
    ./run modules/notion/tool/notion_api.py blocks delete <block_id>

    ./run modules/notion/tool/notion_api.py search <query> [--filter pages|databases]

    ./run modules/notion/tool/notion_api.py users list
    ./run modules/notion/tool/notion_api.py users get <user_id>
    ./run modules/notion/tool/notion_api.py users me

Usage (Module):
    from modules.notion.tool.notion_api import NotionClient
    client = NotionClient()
    results = client.search("project")
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

from .config import get_api_key

NOTION_API_KEY = get_api_key("NOTION_API_KEY")


# --- Custom Exceptions ---

class NotionError(Exception):
    """Base exception for Notion API errors."""
    pass


class NotionAuthError(NotionError):
    """Authentication/token error."""
    pass


class NotionRateLimitError(NotionError):
    """Rate limit exceeded."""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after} seconds.")


class NotionNotFoundError(NotionError):
    """Page/database/block not found."""
    pass


class NotionValidationError(NotionError):
    """Invalid request parameters."""
    pass


class NotionClient:
    """Client for interacting with Notion API."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or NOTION_API_KEY

        if not self.api_key:
            raise ValueError("NOTION_API_KEY not configured. Set it in .env file.")

        try:
            from notion_client import Client
            from notion_client.errors import APIResponseError
            self._APIResponseError = APIResponseError
        except ImportError:
            raise ImportError("notion-client not installed. Run: pip install notion-client")

        self.client = Client(auth=self.api_key)

    def _handle_error(self, error) -> None:
        """Convert notion-client errors to our custom exceptions."""
        code = getattr(error, 'code', None)
        status = getattr(error, 'status', None)

        if code == 'unauthorized' or status == 401:
            raise NotionAuthError("Invalid API key or insufficient permissions")
        elif code == 'object_not_found' or status == 404:
            raise NotionNotFoundError(str(error))
        elif code == 'rate_limited' or status == 429:
            raise NotionRateLimitError()
        elif code == 'validation_error' or status == 400:
            raise NotionValidationError(str(error))
        else:
            raise NotionError(str(error))

    def _request(self, method, *args, **kwargs) -> Any:
        """Make an API request with error handling."""
        try:
            return method(*args, **kwargs)
        except self._APIResponseError as e:
            self._handle_error(e)

    # ==================== Search Operations ====================

    def search(
        self,
        query: str = "",
        filter_type: str = None,
        sort_direction: str = "descending",
        page_size: int = 100
    ) -> List[Dict]:
        """
        Search across workspace.

        Args:
            query: Search query string
            filter_type: Filter by "page" or "database"
            sort_direction: "ascending" or "descending" by last_edited_time
            page_size: Results per page (max 100)

        Returns:
            List of matching pages/databases
        """
        params = {
            "query": query,
            "page_size": min(page_size, 100)
        }

        if filter_type:
            params["filter"] = {"property": "object", "value": filter_type}

        if sort_direction:
            params["sort"] = {
                "direction": sort_direction,
                "timestamp": "last_edited_time"
            }

        response = self._request(self.client.search, **params)
        return response.get("results", [])

    # ==================== Page Operations ====================

    def get_page(self, page_id: str) -> Dict:
        """Get a page by ID."""
        return self._request(self.client.pages.retrieve, page_id=page_id)

    def create_page(
        self,
        parent_id: str,
        title: str,
        properties: Dict = None,
        children: List[Dict] = None,
        icon: str = None,
        parent_type: str = "page"
    ) -> Dict:
        """
        Create a new page.

        Args:
            parent_id: Parent page or database ID
            title: Page title
            properties: Page properties (required for database parents)
            children: Initial content blocks
            icon: Page icon (emoji)
            parent_type: "page" or "database"

        Returns:
            Created page object
        """
        if parent_type == "database":
            parent = {"database_id": parent_id}
            if properties is None:
                properties = {}
            if "title" not in properties and "Name" not in properties:
                properties["Name"] = {"title": [{"text": {"content": title}}]}
        else:
            parent = {"page_id": parent_id}
            properties = {
                "title": {"title": [{"text": {"content": title}}]}
            }

        params = {
            "parent": parent,
            "properties": properties
        }

        if children:
            params["children"] = children
        if icon:
            params["icon"] = {"type": "emoji", "emoji": icon}

        return self._request(self.client.pages.create, **params)

    def update_page(
        self,
        page_id: str,
        properties: Dict = None,
        archived: bool = None,
        icon: str = None
    ) -> Dict:
        """
        Update a page's properties.

        Args:
            page_id: Page ID to update
            properties: Properties to update
            archived: Set to True to archive, False to restore
            icon: New emoji icon

        Returns:
            Updated page object
        """
        params = {"page_id": page_id}

        if properties is not None:
            params["properties"] = properties
        if archived is not None:
            params["archived"] = archived
        if icon is not None:
            params["icon"] = {"type": "emoji", "emoji": icon}

        return self._request(self.client.pages.update, **params)

    def archive_page(self, page_id: str) -> Dict:
        """Archive (trash) a page."""
        return self.update_page(page_id, archived=True)

    def restore_page(self, page_id: str) -> Dict:
        """Restore an archived page."""
        return self.update_page(page_id, archived=False)

    # ==================== Database Operations ====================

    def get_database(self, database_id: str) -> Dict:
        """Get a database by ID."""
        return self._request(self.client.databases.retrieve, database_id=database_id)

    def query_database(
        self,
        database_id: str,
        filter: Dict = None,
        sorts: List[Dict] = None,
        page_size: int = 100,
        start_cursor: str = None
    ) -> Dict:
        """
        Query a database with optional filtering and sorting.

        Args:
            database_id: Database to query
            filter: Filter conditions (Notion filter object)
            sorts: Sort conditions
            page_size: Results per page
            start_cursor: Pagination cursor

        Returns:
            Query results with results, has_more, next_cursor
        """
        params = {
            "database_id": database_id,
            "page_size": min(page_size, 100)
        }

        if filter:
            params["filter"] = filter
        if sorts:
            params["sorts"] = sorts
        if start_cursor:
            params["start_cursor"] = start_cursor

        return self._request(self.client.databases.query, **params)

    def query_database_all(
        self,
        database_id: str,
        filter: Dict = None,
        sorts: List[Dict] = None
    ) -> List[Dict]:
        """
        Query all entries from a database (handles pagination).

        Args:
            database_id: Database to query
            filter: Filter conditions
            sorts: Sort conditions

        Returns:
            List of all matching entries
        """
        all_results = []
        cursor = None

        while True:
            response = self.query_database(
                database_id=database_id,
                filter=filter,
                sorts=sorts,
                start_cursor=cursor
            )
            all_results.extend(response.get("results", []))

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        return all_results

    def create_database(
        self,
        parent_id: str,
        title: str,
        properties: Dict,
        is_inline: bool = False
    ) -> Dict:
        """
        Create a new database.

        Args:
            parent_id: Parent page ID
            title: Database title
            properties: Database schema (property definitions)
            is_inline: If True, create inline database

        Returns:
            Created database object
        """
        params = {
            "parent": {"type": "page_id", "page_id": parent_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties,
            "is_inline": is_inline
        }

        return self._request(self.client.databases.create, **params)

    def update_database(
        self,
        database_id: str,
        title: str = None,
        properties: Dict = None
    ) -> Dict:
        """Update database title or schema."""
        params = {"database_id": database_id}

        if title:
            params["title"] = [{"type": "text", "text": {"content": title}}]
        if properties:
            params["properties"] = properties

        return self._request(self.client.databases.update, **params)

    # ==================== Block Operations ====================

    def get_block(self, block_id: str) -> Dict:
        """Get a block by ID."""
        return self._request(self.client.blocks.retrieve, block_id=block_id)

    def get_block_children(
        self,
        block_id: str,
        page_size: int = 100,
        start_cursor: str = None
    ) -> Dict:
        """Get children blocks of a block/page."""
        params = {
            "block_id": block_id,
            "page_size": min(page_size, 100)
        }
        if start_cursor:
            params["start_cursor"] = start_cursor

        return self._request(self.client.blocks.children.list, **params)

    def get_all_block_children(self, block_id: str) -> List[Dict]:
        """Get all children blocks (handles pagination)."""
        all_blocks = []
        cursor = None

        while True:
            response = self.get_block_children(block_id, start_cursor=cursor)
            all_blocks.extend(response.get("results", []))

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        return all_blocks

    def append_block_children(
        self,
        block_id: str,
        children: List[Dict]
    ) -> Dict:
        """
        Append children blocks to a block/page.

        Args:
            block_id: Parent block or page ID
            children: List of block objects to append

        Returns:
            Response with created blocks
        """
        return self._request(
            self.client.blocks.children.append,
            block_id=block_id,
            children=children
        )

    def update_block(self, block_id: str, block_data: Dict) -> Dict:
        """
        Update a block.

        Args:
            block_id: Block to update
            block_data: New block content (type-specific)

        Returns:
            Updated block object
        """
        return self._request(
            self.client.blocks.update,
            block_id=block_id,
            **block_data
        )

    def delete_block(self, block_id: str) -> Dict:
        """Delete (archive) a block."""
        return self._request(self.client.blocks.delete, block_id=block_id)

    # ==================== User Operations ====================

    def list_users(self, page_size: int = 100) -> List[Dict]:
        """List all users in the workspace."""
        response = self._request(
            self.client.users.list,
            page_size=min(page_size, 100)
        )
        return response.get("results", [])

    def get_user(self, user_id: str) -> Dict:
        """Get a user by ID."""
        return self._request(self.client.users.retrieve, user_id=user_id)

    def get_bot_user(self) -> Dict:
        """Get the bot user (current integration)."""
        return self._request(self.client.users.me)

    # ==================== Helper Methods ====================

    def _parse_inline_markdown(self, text: str) -> List[Dict]:
        """
        Parse inline markdown (links, bold, italic) into Notion rich_text array.

        Supports:
        - Links: [text](url)
        - Bold: **text** or __text__
        - Italic: *text* or _text_
        - Code: `text`
        """
        import re
        rich_text = []

        # Pattern to match markdown links [text](url)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'

        last_end = 0
        for match in re.finditer(link_pattern, text):
            # Add text before the link
            if match.start() > last_end:
                before_text = text[last_end:match.start()]
                if before_text:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": before_text}
                    })

            # Add the link
            link_text = match.group(1)
            link_url = match.group(2)
            rich_text.append({
                "type": "text",
                "text": {
                    "content": link_text,
                    "link": {"url": link_url}
                }
            })
            last_end = match.end()

        # Add remaining text after last link
        if last_end < len(text):
            remaining = text[last_end:]
            if remaining:
                rich_text.append({
                    "type": "text",
                    "text": {"content": remaining}
                })

        # If no links were found, return plain text
        if not rich_text:
            rich_text.append({
                "type": "text",
                "text": {"content": text}
            })

        return rich_text

    def markdown_to_blocks(self, markdown: str) -> List[Dict]:
        """
        Convert simple markdown to Notion blocks.

        Supports:
        - Paragraphs
        - Headings (# ## ###)
        - Bullet lists (- or *)
        - Numbered lists (1. 2.)
        - Code blocks (```)
        - Horizontal rules (---)
        - Checkboxes (- [ ] or - [x])
        - Quotes (>)

        Returns:
            List of Notion block objects
        """
        blocks = []
        lines = markdown.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Code block
            if line.startswith('```'):
                language = line[3:].strip() or "plain text"
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": '\n'.join(code_lines)}}],
                        "language": language
                    }
                })
                i += 1
                continue

            # Headings
            if line.startswith('### '):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": self._parse_inline_markdown(line[4:])
                    }
                })
            elif line.startswith('## '):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": self._parse_inline_markdown(line[3:])
                    }
                })
            elif line.startswith('# '):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": self._parse_inline_markdown(line[2:])
                    }
                })
            # Checkbox
            elif line.startswith('- [ ] ') or line.startswith('- [x] '):
                checked = line.startswith('- [x] ')
                blocks.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": self._parse_inline_markdown(line[6:]),
                        "checked": checked
                    }
                })
            # Bullet list
            elif line.startswith('- ') or line.startswith('* '):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": self._parse_inline_markdown(line[2:])
                    }
                })
            # Numbered list
            elif len(line) > 2 and line[0].isdigit() and line[1:3] in ('. ', ') '):
                blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": self._parse_inline_markdown(line[3:])
                    }
                })
            # Quote
            elif line.startswith('> '):
                blocks.append({
                    "object": "block",
                    "type": "quote",
                    "quote": {
                        "rich_text": self._parse_inline_markdown(line[2:])
                    }
                })
            # Horizontal rule
            elif line.strip() in ['---', '***', '___']:
                blocks.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })
            # Regular paragraph
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self._parse_inline_markdown(line)
                    }
                })

            i += 1

        return blocks

    def blocks_to_markdown(self, blocks: List[Dict]) -> str:
        """Convert Notion blocks to markdown."""
        lines = []

        for block in blocks:
            block_type = block.get("type")

            if block_type == "paragraph":
                text = self._extract_rich_text(block.get("paragraph", {}).get("rich_text", []))
                lines.append(text)
            elif block_type == "heading_1":
                text = self._extract_rich_text(block.get("heading_1", {}).get("rich_text", []))
                lines.append(f"# {text}")
            elif block_type == "heading_2":
                text = self._extract_rich_text(block.get("heading_2", {}).get("rich_text", []))
                lines.append(f"## {text}")
            elif block_type == "heading_3":
                text = self._extract_rich_text(block.get("heading_3", {}).get("rich_text", []))
                lines.append(f"### {text}")
            elif block_type == "bulleted_list_item":
                text = self._extract_rich_text(block.get("bulleted_list_item", {}).get("rich_text", []))
                lines.append(f"- {text}")
            elif block_type == "numbered_list_item":
                text = self._extract_rich_text(block.get("numbered_list_item", {}).get("rich_text", []))
                lines.append(f"1. {text}")
            elif block_type == "code":
                code_block = block.get("code", {})
                text = self._extract_rich_text(code_block.get("rich_text", []))
                language = code_block.get("language", "")
                lines.append(f"```{language}\n{text}\n```")
            elif block_type == "divider":
                lines.append("---")
            elif block_type == "to_do":
                todo = block.get("to_do", {})
                text = self._extract_rich_text(todo.get("rich_text", []))
                checked = "x" if todo.get("checked") else " "
                lines.append(f"- [{checked}] {text}")
            elif block_type == "quote":
                text = self._extract_rich_text(block.get("quote", {}).get("rich_text", []))
                lines.append(f"> {text}")
            elif block_type == "callout":
                text = self._extract_rich_text(block.get("callout", {}).get("rich_text", []))
                icon = block.get("callout", {}).get("icon", {}).get("emoji", "")
                lines.append(f"> {icon} {text}")

        return "\n\n".join(lines)

    def _extract_rich_text(self, rich_text: List[Dict]) -> str:
        """Extract plain text from rich text array."""
        return "".join(item.get("plain_text", "") for item in rich_text)

    @staticmethod
    def normalize_id(id_str: str) -> str:
        """Normalize a Notion ID (remove dashes if present)."""
        return id_str.replace("-", "")

    def get_page_title(self, page: Dict) -> str:
        """Extract title from a page object."""
        props = page.get("properties", {})
        # Try common title property names
        for prop_name in ["title", "Title", "Name", "name"]:
            if prop_name in props:
                title_prop = props[prop_name]
                if title_prop.get("type") == "title":
                    return self._extract_rich_text(title_prop.get("title", []))
        return "Untitled"


# --- CLI Interface ---

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Notion API CLI - Manage pages, databases, blocks, and search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest="category", help="Command category")

    # === Pages ===
    pages_parser = subparsers.add_parser("pages", help="Page operations")
    pages_sub = pages_parser.add_subparsers(dest="action")

    # pages get
    pages_get = pages_sub.add_parser("get", help="Get page by ID")
    pages_get.add_argument("page_id", help="Page ID")

    # pages create
    pages_create = pages_sub.add_parser("create", help="Create a page")
    pages_create.add_argument("parent_id", help="Parent page or database ID")
    pages_create.add_argument("--title", required=True, help="Page title")
    pages_create.add_argument("--content", help="Initial content (markdown)")
    pages_create.add_argument("--content-file", help="File with markdown content")
    pages_create.add_argument("--database", action="store_true",
                              help="Parent is a database")
    pages_create.add_argument("--icon", help="Emoji icon")

    # pages update
    pages_update = pages_sub.add_parser("update", help="Update a page")
    pages_update.add_argument("page_id", help="Page ID")
    pages_update.add_argument("--title", help="New title")
    pages_update.add_argument("--icon", help="New emoji icon")
    pages_update.add_argument("--properties", help="Properties JSON to update")

    # pages archive
    pages_archive = pages_sub.add_parser("archive", help="Archive a page")
    pages_archive.add_argument("page_id", help="Page ID to archive")

    # pages restore
    pages_restore = pages_sub.add_parser("restore", help="Restore an archived page")
    pages_restore.add_argument("page_id", help="Page ID to restore")

    # === Databases ===
    db_parser = subparsers.add_parser("databases", help="Database operations")
    db_sub = db_parser.add_subparsers(dest="action")

    # databases get
    db_get = db_sub.add_parser("get", help="Get database schema")
    db_get.add_argument("database_id", help="Database ID")

    # databases query
    db_query = db_sub.add_parser("query", help="Query database entries")
    db_query.add_argument("database_id", help="Database ID")
    db_query.add_argument("--filter", help="Filter JSON")
    db_query.add_argument("--sorts", help="Sorts JSON")
    db_query.add_argument("--limit", type=int, default=100, help="Max results")
    db_query.add_argument("--all", action="store_true", help="Fetch all results (paginate)")

    # databases create
    db_create = db_sub.add_parser("create", help="Create a database")
    db_create.add_argument("parent_id", help="Parent page ID")
    db_create.add_argument("--title", required=True, help="Database title")
    db_create.add_argument("--properties", required=True, help="Schema JSON")
    db_create.add_argument("--inline", action="store_true", help="Create inline database")

    # databases update
    db_update = db_sub.add_parser("update", help="Update database schema")
    db_update.add_argument("database_id", help="Database ID")
    db_update.add_argument("--title", help="New title")
    db_update.add_argument("--properties", help="Properties to update (JSON)")

    # === Blocks ===
    blocks_parser = subparsers.add_parser("blocks", help="Block operations")
    blocks_sub = blocks_parser.add_subparsers(dest="action")

    # blocks get
    blocks_get = blocks_sub.add_parser("get", help="Get block by ID")
    blocks_get.add_argument("block_id", help="Block ID")

    # blocks children
    blocks_children = blocks_sub.add_parser("children", help="Get block children")
    blocks_children.add_argument("block_id", help="Block or page ID")
    blocks_children.add_argument("--as-markdown", action="store_true",
                                  help="Output as markdown")
    blocks_children.add_argument("--all", action="store_true",
                                  help="Fetch all children (paginate)")

    # blocks append
    blocks_append = blocks_sub.add_parser("append", help="Append content to block/page")
    blocks_append.add_argument("block_id", help="Parent block or page ID")
    blocks_append.add_argument("--content", help="Markdown content")
    blocks_append.add_argument("--content-file", help="File with markdown content")
    blocks_append.add_argument("--json", help="Block JSON directly")

    # blocks delete
    blocks_delete = blocks_sub.add_parser("delete", help="Delete a block")
    blocks_delete.add_argument("block_id", help="Block ID")

    # === Search ===
    search_parser = subparsers.add_parser("search", help="Search workspace")
    search_parser.add_argument("query", nargs="?", default="", help="Search query")
    search_parser.add_argument("--filter", choices=["page", "database"],
                               help="Filter by type")
    search_parser.add_argument("--limit", type=int, default=20, help="Max results")

    # === Users ===
    users_parser = subparsers.add_parser("users", help="User operations")
    users_sub = users_parser.add_subparsers(dest="action")

    users_sub.add_parser("list", help="List all users")
    users_sub.add_parser("me", help="Get bot user info")

    users_get = users_sub.add_parser("get", help="Get user by ID")
    users_get.add_argument("user_id", help="User ID")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.category:
        parser.print_help()
        sys.exit(1)

    try:
        client = NotionClient()
    except (ValueError, ImportError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # === Pages ===
        if args.category == "pages":
            if args.action == "get":
                page = client.get_page(args.page_id)
                title = client.get_page_title(page)
                print(f"Page: {title}", file=sys.stderr)
                print(json.dumps(page, indent=2))

            elif args.action == "create":
                content = args.content
                if args.content_file:
                    with open(args.content_file, 'r') as f:
                        content = f.read()

                children = None
                if content:
                    children = client.markdown_to_blocks(content)

                parent_type = "database" if args.database else "page"
                page = client.create_page(
                    parent_id=args.parent_id,
                    title=args.title,
                    children=children,
                    icon=args.icon,
                    parent_type=parent_type
                )
                print(f"Created page: {page.get('id')}", file=sys.stderr)
                print(json.dumps(page, indent=2))

            elif args.action == "update":
                properties = None
                if args.properties:
                    properties = json.loads(args.properties)
                if args.title:
                    if properties is None:
                        properties = {}
                    properties["title"] = {"title": [{"text": {"content": args.title}}]}

                page = client.update_page(
                    page_id=args.page_id,
                    properties=properties,
                    icon=args.icon
                )
                print(f"Updated page: {args.page_id}", file=sys.stderr)
                print(json.dumps(page, indent=2))

            elif args.action == "archive":
                page = client.archive_page(args.page_id)
                print(f"Archived page: {args.page_id}")

            elif args.action == "restore":
                page = client.restore_page(args.page_id)
                print(f"Restored page: {args.page_id}")

            else:
                parser.parse_args(["pages", "--help"])

        # === Databases ===
        elif args.category == "databases":
            if args.action == "get":
                db = client.get_database(args.database_id)
                title = client._extract_rich_text(db.get("title", []))
                print(f"Database: {title}", file=sys.stderr)
                print(json.dumps(db, indent=2))

            elif args.action == "query":
                filter_obj = json.loads(args.filter) if args.filter else None
                sorts_obj = json.loads(args.sorts) if args.sorts else None

                if args.all:
                    results = client.query_database_all(
                        database_id=args.database_id,
                        filter=filter_obj,
                        sorts=sorts_obj
                    )
                    print(f"Found {len(results)} entries", file=sys.stderr)
                    print(json.dumps(results, indent=2))
                else:
                    response = client.query_database(
                        database_id=args.database_id,
                        filter=filter_obj,
                        sorts=sorts_obj,
                        page_size=args.limit
                    )
                    print(f"Found {len(response.get('results', []))} entries (has_more: {response.get('has_more')})", file=sys.stderr)
                    print(json.dumps(response, indent=2))

            elif args.action == "create":
                properties = json.loads(args.properties)
                db = client.create_database(
                    parent_id=args.parent_id,
                    title=args.title,
                    properties=properties,
                    is_inline=args.inline
                )
                print(f"Created database: {db.get('id')}", file=sys.stderr)
                print(json.dumps(db, indent=2))

            elif args.action == "update":
                properties = json.loads(args.properties) if args.properties else None
                db = client.update_database(
                    database_id=args.database_id,
                    title=args.title,
                    properties=properties
                )
                print(f"Updated database: {db.get('id')}", file=sys.stderr)
                print(json.dumps(db, indent=2))

            else:
                parser.parse_args(["databases", "--help"])

        # === Blocks ===
        elif args.category == "blocks":
            if args.action == "get":
                block = client.get_block(args.block_id)
                print(json.dumps(block, indent=2))

            elif args.action == "children":
                if args.all:
                    blocks = client.get_all_block_children(args.block_id)
                else:
                    response = client.get_block_children(args.block_id)
                    blocks = response.get("results", [])

                print(f"Found {len(blocks)} block(s)", file=sys.stderr)

                if args.as_markdown:
                    markdown = client.blocks_to_markdown(blocks)
                    print(markdown)
                else:
                    print(json.dumps(blocks, indent=2))

            elif args.action == "append":
                content = args.content
                if args.content_file:
                    with open(args.content_file, 'r') as f:
                        content = f.read()

                if args.json:
                    children = json.loads(args.json)
                elif content:
                    children = client.markdown_to_blocks(content)
                else:
                    print("Error: --content, --content-file, or --json required", file=sys.stderr)
                    sys.exit(1)

                response = client.append_block_children(args.block_id, children)
                print(f"Appended {len(children)} block(s)", file=sys.stderr)
                print(json.dumps(response, indent=2))

            elif args.action == "delete":
                client.delete_block(args.block_id)
                print(f"Deleted block: {args.block_id}")

            else:
                parser.parse_args(["blocks", "--help"])

        # === Search ===
        elif args.category == "search":
            results = client.search(
                query=args.query,
                filter_type=args.filter,
                page_size=args.limit
            )
            print(f"Found {len(results)} result(s):", file=sys.stderr)
            for item in results:
                obj_type = item.get("object", "unknown")
                if obj_type == "page":
                    title = client.get_page_title(item)
                else:
                    title = client._extract_rich_text(item.get("title", []))
                print(f"  [{obj_type}] {title} ({item.get('id')})", file=sys.stderr)
            print(json.dumps(results, indent=2))

        # === Users ===
        elif args.category == "users":
            if args.action == "list":
                users = client.list_users()
                print(f"Found {len(users)} user(s):", file=sys.stderr)
                for user in users:
                    user_type = user.get("type", "unknown")
                    name = user.get("name", "Unknown")
                    print(f"  [{user_type}] {name} ({user.get('id')})", file=sys.stderr)
                print(json.dumps(users, indent=2))

            elif args.action == "me":
                bot = client.get_bot_user()
                print(f"Bot: {bot.get('name')}", file=sys.stderr)
                print(json.dumps(bot, indent=2))

            elif args.action == "get":
                user = client.get_user(args.user_id)
                print(json.dumps(user, indent=2))

            else:
                parser.parse_args(["users", "--help"])

        else:
            parser.print_help()
            sys.exit(1)

    except NotionError as e:
        print(f"Notion API error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

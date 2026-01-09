#!/usr/bin/env python3
"""
Notion API Integration Script

Execution tool for managing Notion pages, databases, blocks, comments, and users via the API.
Supports: pages, databases, data_sources, blocks, comments, search, and users.

Usage (CLI):
    ./run tool/notion_api.py pages get <page_id>
    ./run tool/notion_api.py pages create <parent_id> --title "Title" [--content "Markdown"] [--properties JSON]
    ./run tool/notion_api.py pages update <page_id> --title "New Title"
    ./run tool/notion_api.py pages archive <page_id>
    ./run tool/notion_api.py pages restore <page_id>
    ./run tool/notion_api.py pages create-batch <database_id> --file entries.json
    ./run tool/notion_api.py pages update-batch --file updates.json

    ./run tool/notion_api.py databases get <database_id>
    ./run tool/notion_api.py databases query <database_id> [--filter JSON] [--sorts JSON]
    ./run tool/notion_api.py databases create <parent_id> --title "Title" --properties JSON
    ./run tool/notion_api.py databases update <database_id> --properties JSON  # Legacy, may not work

    ./run tool/notion_api.py data_sources get <data_source_id>
    ./run tool/notion_api.py data_sources update <data_source_id> --properties JSON

    ./run tool/notion_api.py blocks get <block_id>
    ./run tool/notion_api.py blocks children <block_id> [--as-markdown] [--all] [--recursive]
    ./run tool/notion_api.py blocks append <parent_id> --content "Markdown" [--after <block_id>]
    ./run tool/notion_api.py blocks update <block_id> --type <block_type> --content "New text"
    ./run tool/notion_api.py blocks delete <block_id>
    ./run tool/notion_api.py blocks delete-batch <id1> <id2> <id3>

    ./run tool/notion_api.py comments list <page_id>
    ./run tool/notion_api.py comments create <page_id> --content "Comment text" [--discussion <id>]

    ./run tool/notion_api.py search <query> [--filter pages|databases]

    ./run tool/notion_api.py users list
    ./run tool/notion_api.py users get <user_id>
    ./run tool/notion_api.py users me

Note: For schema modifications (adding properties), use data_sources update instead
of databases update. The databases.update endpoint is deprecated for schema changes.

Markdown Conversion: The tool converts **bold**, *italic*, `code`, ~~strikethrough~~,
and [links](url) to proper Notion annotations.

Usage (Module):
    from modules.notion.tool.notion_api import NotionClient
    client = NotionClient()
    results = client.search("project")

    # Use property helpers for database entries
    page = client.create_page(
        parent_id="db-id",
        title="Task",
        properties={
            "Status": client.prop_select("Open"),
            "Priority": client.prop_select("High"),
            "Project": client.prop_relation(["project-id"]),
        },
        parent_type="database"
    )
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
            # API expects "data_source" not "database"
            api_filter_type = "data_source" if filter_type == "database" else filter_type
            params["filter"] = {"property": "object", "value": api_filter_type}

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
            "data_source_id": database_id,
            "page_size": min(page_size, 100)
        }

        if filter:
            params["filter"] = filter
        if sorts:
            params["sorts"] = sorts
        if start_cursor:
            params["start_cursor"] = start_cursor

        # Notion API uses data_sources.query for database queries
        return self._request(self.client.data_sources.query, **params)

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
        """
        Update database title or schema.

        NOTE: This uses the legacy databases.update endpoint which may not work
        for adding new properties. Use update_data_source() instead for schema
        modifications.
        """
        params = {"database_id": database_id}

        if title:
            params["title"] = [{"type": "text", "text": {"content": title}}]
        if properties:
            params["properties"] = properties

        return self._request(self.client.databases.update, **params)

    # ==================== Data Source Operations ====================

    def get_data_source(self, data_source_id: str) -> Dict:
        """
        Get a data source by ID.

        Data sources are Notion's new architecture for databases. Use this to
        retrieve the full schema including properties.

        Args:
            data_source_id: Data source ID (can find via search with filter=database)

        Returns:
            Data source object with properties schema
        """
        return self._request(self.client.data_sources.retrieve, data_source_id=data_source_id)

    def update_data_source(
        self,
        data_source_id: str,
        properties: Dict = None
    ) -> Dict:
        """
        Update a data source's properties schema.

        This is the correct method for adding/modifying database properties
        in Notion's new architecture. The databases.update endpoint no longer
        works reliably for schema modifications.

        Args:
            data_source_id: Data source ID (NOT the database ID)
            properties: Properties to add or update

        Returns:
            Updated data source object

        Example:
            # Add a select property
            client.update_data_source("data-source-id", properties={
                "Priority": {
                    "select": {
                        "options": [
                            {"name": "High", "color": "red"},
                            {"name": "Medium", "color": "yellow"},
                            {"name": "Low", "color": "green"}
                        ]
                    }
                }
            })

            # Add a relation property
            client.update_data_source("data-source-id", properties={
                "Project": {
                    "relation": {
                        "data_source_id": "target-data-source-id",
                        "type": "dual_property",
                        "dual_property": {"synced_property_name": "Related Items"}
                    }
                }
            })
        """
        params = {"data_source_id": data_source_id}

        if properties:
            params["properties"] = properties

        return self._request(self.client.data_sources.update, **params)

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

    def get_all_block_children_recursive(
        self,
        block_id: str,
        max_depth: int = 10
    ) -> List[Dict]:
        """
        Get all children blocks recursively (handles nested structures).

        Args:
            block_id: Parent block or page ID
            max_depth: Maximum recursion depth (default 10)

        Returns:
            List of blocks with nested children populated in 'children' key
        """
        def fetch_children(parent_id: str, depth: int) -> List[Dict]:
            if depth > max_depth:
                return []

            blocks = self.get_all_block_children(parent_id)

            for block in blocks:
                if block.get("has_children"):
                    block["children"] = fetch_children(block["id"], depth + 1)

            return blocks

        return fetch_children(block_id, 0)

    def append_block_children(
        self,
        block_id: str,
        children: List[Dict],
        after: str = None
    ) -> Dict:
        """
        Append children blocks to a block/page.

        Args:
            block_id: Parent block or page ID
            children: List of block objects to append
            after: Block ID to insert after (optional). If provided, new blocks
                   are inserted after this block instead of at the end.

        Returns:
            Response with created blocks
        """
        params = {
            "block_id": block_id,
            "children": children
        }
        if after:
            params["after"] = after

        return self._request(
            self.client.blocks.children.append,
            **params
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

    # ==================== Comment Operations ====================

    def list_comments(self, block_id: str, page_size: int = 100) -> List[Dict]:
        """
        List comments on a block or page.

        Args:
            block_id: Page or block ID to get comments from
            page_size: Results per page (max 100)

        Returns:
            List of comment objects
        """
        response = self._request(
            self.client.comments.list,
            block_id=block_id,
            page_size=min(page_size, 100)
        )
        return response.get("results", [])

    def create_comment(
        self,
        parent_id: str,
        content: str,
        discussion_id: str = None
    ) -> Dict:
        """
        Create a comment on a page or reply to an existing discussion.

        Args:
            parent_id: Page ID to comment on (if new discussion)
            content: Comment text
            discussion_id: Existing discussion ID (to reply to thread)

        Returns:
            Created comment object
        """
        rich_text = [{"type": "text", "text": {"content": content}}]

        params = {"rich_text": rich_text}

        if discussion_id:
            params["discussion_id"] = discussion_id
        else:
            params["parent"] = {"page_id": parent_id}

        return self._request(self.client.comments.create, **params)

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
        Parse inline markdown into Notion rich_text array.

        Supports:
        - Links: [text](url)
        - Bold: **text**
        - Italic: *text* (single asterisk, not inside **)
        - Code: `text`
        - Strikethrough: ~~text~~
        """
        import re

        # Combined pattern for all inline formatting
        # Order matters: longer patterns first (bold before italic)
        pattern = r'(\*\*(.+?)\*\*)|(\*([^*]+?)\*)|(~~(.+?)~~)|(`([^`]+?)`)|(\[([^\]]+)\]\(([^)]+)\))'

        rich_text = []
        last_end = 0

        for match in re.finditer(pattern, text):
            # Add plain text before match
            if match.start() > last_end:
                plain = text[last_end:match.start()]
                if plain:
                    rich_text.append({"type": "text", "text": {"content": plain}})

            if match.group(1):  # Bold **text**
                rich_text.append({
                    "type": "text",
                    "text": {"content": match.group(2)},
                    "annotations": {"bold": True}
                })
            elif match.group(3):  # Italic *text*
                rich_text.append({
                    "type": "text",
                    "text": {"content": match.group(4)},
                    "annotations": {"italic": True}
                })
            elif match.group(5):  # Strikethrough ~~text~~
                rich_text.append({
                    "type": "text",
                    "text": {"content": match.group(6)},
                    "annotations": {"strikethrough": True}
                })
            elif match.group(7):  # Code `text`
                rich_text.append({
                    "type": "text",
                    "text": {"content": match.group(8)},
                    "annotations": {"code": True}
                })
            elif match.group(9):  # Link [text](url)
                rich_text.append({
                    "type": "text",
                    "text": {"content": match.group(10), "link": {"url": match.group(11)}}
                })

            last_end = match.end()

        # Add remaining text after last match
        if last_end < len(text):
            remaining = text[last_end:]
            if remaining:
                rich_text.append({"type": "text", "text": {"content": remaining}})

        # If no formatting found, return plain text
        if not rich_text:
            rich_text.append({"type": "text", "text": {"content": text}})

        return rich_text

    def _parse_markdown_table(self, table_lines: List[str]) -> Dict:
        """
        Parse markdown table lines into a Notion table block.

        Args:
            table_lines: List of markdown table lines (including header and separator)

        Returns:
            Notion table block object
        """
        import re

        # Parse each row into cells
        def parse_row(line: str) -> List[str]:
            # Strip leading/trailing pipes and split
            line = line.strip()
            if line.startswith('|'):
                line = line[1:]
            if line.endswith('|'):
                line = line[:-1]
            return [cell.strip() for cell in line.split('|')]

        # Check if a line is a separator row (|---|---|)
        def is_separator(line: str) -> bool:
            return bool(re.match(r'^\|?[\s\-:]+(\|[\s\-:]+)+\|?$', line.strip()))

        rows = []
        has_header = False

        for idx, line in enumerate(table_lines):
            if is_separator(line):
                # If separator is second row, first row was header
                if idx == 1:
                    has_header = True
                continue
            rows.append(parse_row(line))

        if not rows:
            return None

        # Determine table width from first row
        table_width = len(rows[0])

        # Build table rows for Notion
        table_rows = []
        for row in rows:
            # Pad or trim row to match width
            cells = row[:table_width]
            while len(cells) < table_width:
                cells.append("")

            # Convert each cell to rich_text array
            notion_cells = [
                self._parse_inline_markdown(cell) for cell in cells
            ]

            table_rows.append({
                "type": "table_row",
                "table_row": {
                    "cells": notion_cells
                }
            })

        return {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": table_width,
                "has_column_header": has_header,
                "children": table_rows
            }
        }

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
        - Tables (| col | col |)

        Returns:
            List of Notion block objects
        """
        import re

        blocks = []
        lines = markdown.split('\n')
        i = 0

        # Helper to detect table rows
        def is_table_row(line: str) -> bool:
            stripped = line.strip()
            return stripped.startswith('|') and stripped.endswith('|') and stripped.count('|') >= 2

        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Table detection - collect consecutive table lines
            if is_table_row(line):
                table_lines = []
                while i < len(lines) and (is_table_row(lines[i]) or re.match(r'^\|?[\s\-:]+(\|[\s\-:]+)+\|?$', lines[i].strip())):
                    table_lines.append(lines[i])
                    i += 1
                if table_lines:
                    table_block = self._parse_markdown_table(table_lines)
                    if table_block:
                        blocks.append(table_block)
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

    # ==================== Property Value Helpers ====================
    # These helper methods make it easier to construct property values
    # for database entries when using the Python module.

    @staticmethod
    def prop_title(text: str) -> Dict:
        """Create title property value."""
        return {"title": [{"text": {"content": text}}]}

    @staticmethod
    def prop_text(text: str) -> Dict:
        """Create rich_text property value."""
        return {"rich_text": [{"text": {"content": text}}]}

    @staticmethod
    def prop_select(name: str) -> Dict:
        """Create select property value."""
        return {"select": {"name": name}}

    @staticmethod
    def prop_multi_select(names: List[str]) -> Dict:
        """Create multi_select property value."""
        return {"multi_select": [{"name": n} for n in names]}

    @staticmethod
    def prop_date(start: str, end: str = None) -> Dict:
        """Create date property value. Dates should be ISO 8601 format (YYYY-MM-DD)."""
        date = {"start": start}
        if end:
            date["end"] = end
        return {"date": date}

    @staticmethod
    def prop_relation(ids: List[str]) -> Dict:
        """Create relation property value from list of page IDs."""
        return {"relation": [{"id": id} for id in ids]}

    @staticmethod
    def prop_checkbox(checked: bool) -> Dict:
        """Create checkbox property value."""
        return {"checkbox": checked}

    @staticmethod
    def prop_number(value: float) -> Dict:
        """Create number property value."""
        return {"number": value}

    @staticmethod
    def prop_url(url: str) -> Dict:
        """Create url property value."""
        return {"url": url}

    @staticmethod
    def prop_email(email: str) -> Dict:
        """Create email property value."""
        return {"email": email}

    @staticmethod
    def prop_phone(phone: str) -> Dict:
        """Create phone_number property value."""
        return {"phone_number": phone}

    # ==================== Batch Operations ====================
    # These methods handle bulk operations with rate limiting and
    # partial failure handling.

    def _throttle(self, delay: float = 0.35):
        """
        Throttle API requests to stay under rate limits.
        Notion allows ~3 requests/second average, so ~0.33s delay between requests.
        Using 0.35s for safety margin.
        """
        import time
        time.sleep(delay)

    def create_pages_batch(
        self,
        database_id: str,
        entries: List[Dict],
        on_progress: callable = None
    ) -> Dict:
        """
        Create multiple database entries in batch.

        Args:
            database_id: Target database ID
            entries: List of entry definitions, each with:
                - title: Entry title (required)
                - properties: Additional properties (optional)
                - content: Markdown content for page body (optional)
                - icon: Emoji icon (optional)
            on_progress: Optional callback(current, total, result) for progress

        Returns:
            Dict with:
                - created: List of created page objects
                - failed: List of {index, entry, error} for failures
                - total: Total entries attempted
                - success_count: Number of successes
                - failure_count: Number of failures

        Example:
            entries = [
                {"title": "Task 1", "properties": {"Status": {"select": {"name": "Open"}}}},
                {"title": "Task 2", "properties": {"Priority": {"select": {"name": "High"}}}},
            ]
            result = client.create_pages_batch("db-id", entries)
        """
        created = []
        failed = []

        for i, entry in enumerate(entries):
            try:
                title = entry.get("title", "Untitled")
                properties = entry.get("properties", {})
                content = entry.get("content")
                icon = entry.get("icon")

                # Ensure title is set in properties
                if "Name" not in properties and "title" not in properties:
                    properties["Name"] = {"title": [{"text": {"content": title}}]}

                children = None
                if content:
                    children = self.markdown_to_blocks(content)

                page = self.create_page(
                    parent_id=database_id,
                    title=title,
                    properties=properties,
                    children=children,
                    icon=icon,
                    parent_type="database"
                )
                created.append(page)

                if on_progress:
                    on_progress(i + 1, len(entries), {"success": True, "page": page})

            except Exception as e:
                failed.append({
                    "index": i,
                    "entry": entry,
                    "error": str(e)
                })
                if on_progress:
                    on_progress(i + 1, len(entries), {"success": False, "error": str(e)})

            # Throttle between requests (skip after last item)
            if i < len(entries) - 1:
                self._throttle()

        return {
            "created": created,
            "failed": failed,
            "total": len(entries),
            "success_count": len(created),
            "failure_count": len(failed)
        }

    def update_pages_batch(
        self,
        updates: List[Dict],
        on_progress: callable = None
    ) -> Dict:
        """
        Update multiple pages in batch.

        Args:
            updates: List of update definitions, each with:
                - page_id: Page ID to update (required)
                - properties: Properties to update (optional)
                - icon: New emoji icon (optional)
                - archived: Set archived status (optional)
            on_progress: Optional callback(current, total, result) for progress

        Returns:
            Dict with:
                - updated: List of updated page objects
                - failed: List of {index, update, error} for failures
                - total: Total updates attempted
                - success_count: Number of successes
                - failure_count: Number of failures

        Example:
            updates = [
                {"page_id": "id1", "properties": {"Status": {"select": {"name": "Done"}}}},
                {"page_id": "id2", "icon": "✅"},
            ]
            result = client.update_pages_batch(updates)
        """
        updated = []
        failed = []

        for i, update in enumerate(updates):
            try:
                page_id = update.get("page_id")
                if not page_id:
                    raise ValueError("page_id is required")

                page = self.update_page(
                    page_id=page_id,
                    properties=update.get("properties"),
                    icon=update.get("icon"),
                    archived=update.get("archived")
                )
                updated.append(page)

                if on_progress:
                    on_progress(i + 1, len(updates), {"success": True, "page": page})

            except Exception as e:
                failed.append({
                    "index": i,
                    "update": update,
                    "error": str(e)
                })
                if on_progress:
                    on_progress(i + 1, len(updates), {"success": False, "error": str(e)})

            # Throttle between requests
            if i < len(updates) - 1:
                self._throttle()

        return {
            "updated": updated,
            "failed": failed,
            "total": len(updates),
            "success_count": len(updated),
            "failure_count": len(failed)
        }

    def delete_blocks_batch(
        self,
        block_ids: List[str],
        on_progress: callable = None
    ) -> Dict:
        """
        Delete multiple blocks in batch.

        Args:
            block_ids: List of block IDs to delete
            on_progress: Optional callback(current, total, result) for progress

        Returns:
            Dict with:
                - deleted: List of deleted block IDs
                - failed: List of {index, block_id, error} for failures
                - total: Total deletions attempted
                - success_count: Number of successes
                - failure_count: Number of failures

        Example:
            result = client.delete_blocks_batch(["block-id-1", "block-id-2", "block-id-3"])
        """
        deleted = []
        failed = []

        for i, block_id in enumerate(block_ids):
            try:
                self.delete_block(block_id)
                deleted.append(block_id)

                if on_progress:
                    on_progress(i + 1, len(block_ids), {"success": True, "block_id": block_id})

            except Exception as e:
                failed.append({
                    "index": i,
                    "block_id": block_id,
                    "error": str(e)
                })
                if on_progress:
                    on_progress(i + 1, len(block_ids), {"success": False, "error": str(e)})

            # Throttle between requests
            if i < len(block_ids) - 1:
                self._throttle()

        return {
            "deleted": deleted,
            "failed": failed,
            "total": len(block_ids),
            "success_count": len(deleted),
            "failure_count": len(failed)
        }


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
    pages_create.add_argument("--properties", help="Additional properties JSON (for database entries)")

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

    # pages create-batch
    pages_create_batch = pages_sub.add_parser("create-batch", help="Create multiple database entries")
    pages_create_batch.add_argument("database_id", help="Target database ID")
    pages_create_batch.add_argument("--file", help="JSON file with entries array")
    pages_create_batch.add_argument("--json", dest="entries_json", help="Entries as JSON array string")

    # pages update-batch
    pages_update_batch = pages_sub.add_parser("update-batch", help="Update multiple pages")
    pages_update_batch.add_argument("--file", help="JSON file with updates array")
    pages_update_batch.add_argument("--json", dest="updates_json", help="Updates as JSON array string")

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

    # === Data Sources ===
    ds_parser = subparsers.add_parser("data_sources", help="Data source operations (for schema updates)")
    ds_sub = ds_parser.add_subparsers(dest="action")

    # data_sources get
    ds_get = ds_sub.add_parser("get", help="Get data source by ID")
    ds_get.add_argument("data_source_id", help="Data source ID")

    # data_sources update
    ds_update = ds_sub.add_parser("update", help="Update data source schema (add/modify properties)")
    ds_update.add_argument("data_source_id", help="Data source ID")
    ds_update.add_argument("--properties", required=True, help="Properties to add/update (JSON)")

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
    blocks_children.add_argument("--recursive", action="store_true",
                                  help="Recursively fetch nested children (toggles, columns, etc.)")

    # blocks append
    blocks_append = blocks_sub.add_parser("append", help="Append content to block/page")
    blocks_append.add_argument("block_id", help="Parent block or page ID")
    blocks_append.add_argument("--content", help="Markdown content")
    blocks_append.add_argument("--content-file", help="File with markdown content")
    blocks_append.add_argument("--json", help="Block JSON directly")
    blocks_append.add_argument("--after", help="Block ID to insert after (instead of appending at end)")

    # blocks delete
    blocks_delete = blocks_sub.add_parser("delete", help="Delete a block")
    blocks_delete.add_argument("block_id", help="Block ID")

    # blocks delete-batch
    blocks_delete_batch = blocks_sub.add_parser("delete-batch", help="Delete multiple blocks")
    blocks_delete_batch.add_argument("block_ids", nargs="+", help="Block IDs to delete")

    # blocks update
    blocks_update = blocks_sub.add_parser("update", help="Update a block")
    blocks_update.add_argument("block_id", help="Block ID to update")
    blocks_update.add_argument("--type", required=True, help="Block type (paragraph, heading_1, etc.)")
    blocks_update.add_argument("--content", help="New text content")
    blocks_update.add_argument("--json", dest="block_json", help="Full block data as JSON")

    # === Search ===
    search_parser = subparsers.add_parser("search", help="Search workspace")
    search_parser.add_argument("query", nargs="?", default="", help="Search query")
    search_parser.add_argument("--filter", choices=["page", "database"],
                               help="Filter by type")
    search_parser.add_argument("--limit", type=int, default=20, help="Max results")

    # === Comments ===
    comments_parser = subparsers.add_parser("comments", help="Comment operations")
    comments_sub = comments_parser.add_subparsers(dest="action")

    # comments list
    comments_list = comments_sub.add_parser("list", help="List comments on a page/block")
    comments_list.add_argument("block_id", help="Page or block ID")

    # comments create
    comments_create = comments_sub.add_parser("create", help="Create a comment")
    comments_create.add_argument("page_id", help="Page ID")
    comments_create.add_argument("--content", required=True, help="Comment text")
    comments_create.add_argument("--discussion", help="Discussion ID (to reply to existing thread)")

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

                # Parse additional properties for database entries
                properties = None
                if getattr(args, 'properties', None):
                    properties = json.loads(args.properties)
                    # Ensure title is set
                    if "Name" not in properties and "title" not in properties:
                        properties["Name"] = {"title": [{"text": {"content": args.title}}]}

                page = client.create_page(
                    parent_id=args.parent_id,
                    title=args.title,
                    properties=properties,
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

            elif args.action == "create-batch":
                # Load entries from file or JSON string
                if args.file:
                    with open(args.file, 'r') as f:
                        entries = json.load(f)
                elif args.entries_json:
                    entries = json.loads(args.entries_json)
                else:
                    print("Error: --file or --json required", file=sys.stderr)
                    sys.exit(1)

                if not isinstance(entries, list):
                    print("Error: entries must be a JSON array", file=sys.stderr)
                    sys.exit(1)

                print(f"Creating {len(entries)} entries...", file=sys.stderr)

                def progress_callback(current, total, result):
                    status = "✓" if result.get("success") else "✗"
                    print(f"  [{current}/{total}] {status}", file=sys.stderr)

                result = client.create_pages_batch(
                    database_id=args.database_id,
                    entries=entries,
                    on_progress=progress_callback
                )

                print(f"\nCompleted: {result['success_count']} created, {result['failure_count']} failed", file=sys.stderr)
                print(json.dumps(result, indent=2))

            elif args.action == "update-batch":
                # Load updates from file or JSON string
                if args.file:
                    with open(args.file, 'r') as f:
                        updates = json.load(f)
                elif args.updates_json:
                    updates = json.loads(args.updates_json)
                else:
                    print("Error: --file or --json required", file=sys.stderr)
                    sys.exit(1)

                if not isinstance(updates, list):
                    print("Error: updates must be a JSON array", file=sys.stderr)
                    sys.exit(1)

                print(f"Updating {len(updates)} pages...", file=sys.stderr)

                def progress_callback(current, total, result):
                    status = "✓" if result.get("success") else "✗"
                    print(f"  [{current}/{total}] {status}", file=sys.stderr)

                result = client.update_pages_batch(
                    updates=updates,
                    on_progress=progress_callback
                )

                print(f"\nCompleted: {result['success_count']} updated, {result['failure_count']} failed", file=sys.stderr)
                print(json.dumps(result, indent=2))

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

        # === Data Sources ===
        elif args.category == "data_sources":
            if args.action == "get":
                ds = client.get_data_source(args.data_source_id)
                print(f"Data source: {args.data_source_id}", file=sys.stderr)
                print(json.dumps(ds, indent=2))

            elif args.action == "update":
                properties = json.loads(args.properties)
                ds = client.update_data_source(
                    data_source_id=args.data_source_id,
                    properties=properties
                )
                print(f"Updated data source: {args.data_source_id}", file=sys.stderr)
                print(json.dumps(ds, indent=2))

            else:
                parser.parse_args(["data_sources", "--help"])

        # === Blocks ===
        elif args.category == "blocks":
            if args.action == "get":
                block = client.get_block(args.block_id)
                print(json.dumps(block, indent=2))

            elif args.action == "children":
                if getattr(args, 'recursive', False):
                    blocks = client.get_all_block_children_recursive(args.block_id)
                elif args.all:
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

                response = client.append_block_children(
                    args.block_id,
                    children,
                    after=getattr(args, 'after', None)
                )
                location = f"after {args.after}" if getattr(args, 'after', None) else "at end"
                print(f"Appended {len(children)} block(s) {location}", file=sys.stderr)
                print(json.dumps(response, indent=2))

            elif args.action == "delete":
                client.delete_block(args.block_id)
                print(f"Deleted block: {args.block_id}")

            elif args.action == "delete-batch":
                block_ids = args.block_ids
                print(f"Deleting {len(block_ids)} blocks...", file=sys.stderr)

                def progress_callback(current, total, result):
                    status = "✓" if result.get("success") else "✗"
                    print(f"  [{current}/{total}] {status}", file=sys.stderr)

                result = client.delete_blocks_batch(
                    block_ids=block_ids,
                    on_progress=progress_callback
                )

                print(f"\nCompleted: {result['success_count']} deleted, {result['failure_count']} failed", file=sys.stderr)
                print(json.dumps(result, indent=2))

            elif args.action == "update":
                if args.block_json:
                    block_data = json.loads(args.block_json)
                elif args.content:
                    block_data = {
                        args.type: {
                            "rich_text": [{"type": "text", "text": {"content": args.content}}]
                        }
                    }
                else:
                    print("Error: --content or --json required", file=sys.stderr)
                    sys.exit(1)

                block = client.update_block(args.block_id, block_data)
                print(f"Updated block: {args.block_id}", file=sys.stderr)
                print(json.dumps(block, indent=2))

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

        # === Comments ===
        elif args.category == "comments":
            if args.action == "list":
                comments = client.list_comments(args.block_id)
                print(f"Found {len(comments)} comment(s)", file=sys.stderr)
                print(json.dumps(comments, indent=2))

            elif args.action == "create":
                comment = client.create_comment(
                    parent_id=args.page_id,
                    content=args.content,
                    discussion_id=getattr(args, 'discussion', None)
                )
                print(f"Created comment: {comment.get('id')}", file=sys.stderr)
                print(json.dumps(comment, indent=2))

            else:
                parser.parse_args(["comments", "--help"])

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

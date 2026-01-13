#!/usr/bin/env python3
"""Notion MCP Server - Fast Notion API access for AI agents."""

from fastmcp import FastMCP
from typing import Optional, Dict, List, Any

mcp = FastMCP("Notion")
_client = None


def get_client():
    """Lazy initialization - only fails when actually used without config."""
    global _client
    if _client is None:
        from .config import get_api_key
        from .notion_api import NotionClient

        api_key = get_api_key("NOTION_API_KEY")
        if not api_key:
            raise ValueError(
                "NOTION_API_KEY not configured. "
                "Add to ~/.config/cc-plugins/.env or run /notion:setup"
            )
        _client = NotionClient()
    return _client


# === Page Operations ===


@mcp.tool
def create_page(
    parent_id: str,
    title: str,
    content: Optional[str] = None,
    parent_type: str = "page",
    icon: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
) -> dict:
    """Create a Notion page or database entry.

    Args:
        parent_id: Parent page or database ID
        title: Page title
        content: Optional markdown content
        parent_type: "page" or "database"
        icon: Optional emoji icon
        properties: Optional additional properties for database entries
    """
    children = None
    if content:
        children = get_client().markdown_to_blocks(content)
    return get_client().create_page(
        parent_id=parent_id,
        title=title,
        properties=properties,
        children=children,
        icon=icon,
        parent_type=parent_type,
    )


@mcp.tool
def get_page(page_id: str) -> dict:
    """Get a Notion page by ID."""
    return get_client().get_page(page_id)


@mcp.tool
def update_page(
    page_id: str,
    title: Optional[str] = None,
    icon: Optional[str] = None,
    archived: Optional[bool] = None,
    properties: Optional[Dict[str, Any]] = None,
) -> dict:
    """Update a Notion page.

    Args:
        page_id: The page ID to update
        title: New title (optional)
        icon: New emoji icon (optional)
        archived: Set to true to archive the page (optional)
        properties: Additional properties to update (optional)
    """
    if properties is None:
        properties = {}
    if title:
        properties["title"] = {"title": [{"text": {"content": title}}]}
    return get_client().update_page(
        page_id=page_id,
        properties=properties if properties else None,
        icon=icon,
        archived=archived,
    )


# === Block Operations ===


@mcp.tool
def get_blocks(block_id: str, as_markdown: bool = True) -> str:
    """Get child blocks of a page/block, optionally as markdown.

    Args:
        block_id: The page or block ID
        as_markdown: If true, return as markdown string; otherwise return raw blocks
    """
    if as_markdown:
        return get_client().get_page_markdown(block_id)
    return get_client().get_block_children(block_id)


@mcp.tool
def append_blocks(parent_id: str, content: str) -> dict:
    """Append markdown content as blocks to a page.

    Args:
        parent_id: The page or block ID to append to
        content: Markdown content to append
    """
    children = get_client().markdown_to_blocks(content)
    return get_client().append_block_children(parent_id, children)


@mcp.tool
def delete_block(block_id: str) -> dict:
    """Delete a block.

    Args:
        block_id: The block ID to delete
    """
    return get_client().delete_block(block_id)


# === Database Operations ===


@mcp.tool
def query_database(
    database_id: str,
    filter: Optional[Dict] = None,
    sorts: Optional[List] = None,
    page_size: int = 100,
) -> dict:
    """Query a Notion database with optional filters and sorts.

    Args:
        database_id: The database ID to query
        filter: Optional filter object (Notion filter format)
        sorts: Optional list of sort objects
        page_size: Number of results to return (default 100)
    """
    return get_client().query_database(
        database_id, filter=filter, sorts=sorts, page_size=page_size
    )


@mcp.tool
def get_database(database_id: str) -> dict:
    """Get database schema and metadata.

    Args:
        database_id: The database ID
    """
    return get_client().get_database(database_id)


# === Search ===


@mcp.tool
def search(query: str, filter_type: Optional[str] = None) -> dict:
    """Search Notion for pages or databases.

    Args:
        query: Search query
        filter_type: Optional "page" or "database" filter
    """
    return get_client().search(query, filter=filter_type)


# === Users ===


@mcp.tool
def list_users() -> dict:
    """List all users in the workspace."""
    return get_client().list_users()


@mcp.tool
def get_me() -> dict:
    """Get the current bot user."""
    return get_client().get_bot_user()


if __name__ == "__main__":
    mcp.run()

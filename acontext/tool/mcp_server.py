"""AContext MCP Server - Context data platform access for AI agents."""

from fastmcp import FastMCP
from typing import Optional

mcp = FastMCP("AContext")
_client = None
_default_disk_id = None


def get_client():
    """Lazy initialization - only fails when actually used without config."""
    global _client
    if _client is None:
        from .config import get_api_key
        from .acontext_api import AContextClient

        base_url = get_api_key("ACONTEXT_BASE_URL")
        api_key = get_api_key("ACONTEXT_API_KEY")
        if not base_url or not api_key:
            raise ValueError(
                "ACONTEXT_BASE_URL and ACONTEXT_API_KEY not configured. "
                "Add to ~/.config/cc-plugins/.env"
            )
        _client = AContextClient(base_url, api_key)
    return _client


def get_default_disk_id() -> str:
    """Get or create a default disk for file operations."""
    global _default_disk_id
    if _default_disk_id is None:
        from .config import get_api_key

        configured = get_api_key("ACONTEXT_DISK_ID")
        if configured:
            _default_disk_id = configured
        else:
            result = get_client().list_disks()
            items = result.get("data", {}).get("items", [])
            if items:
                _default_disk_id = items[0]["id"]
            else:
                created = get_client().create_disk()
                _default_disk_id = created["data"]["id"]
    return _default_disk_id


# === Session Operations ===


@mcp.tool
def session_list() -> dict:
    """List all context sessions. Returns session IDs, configs, and timestamps."""
    return get_client().list_sessions()


@mcp.tool
def session_create(name: Optional[str] = None) -> dict:
    """Create a new context session for tracking a conversation or task.

    Args:
        name: Optional session name/label
    """
    return get_client().create_session(name)


@mcp.tool
def session_delete(session_id: str) -> dict:
    """Delete a session and all its messages.

    Args:
        session_id: The session UUID to delete
    """
    return get_client().delete_session(session_id)


@mcp.tool
def session_store_message(
    session_id: str,
    role: str,
    content: str,
    meta: Optional[dict] = None,
) -> dict:
    """Store a message in a session.

    Args:
        session_id: The session UUID
        role: Message role (user, assistant, system)
        content: Message text content
        meta: Optional metadata dict (tags, source, etc.)
    """
    return get_client().store_message(session_id, role, content, meta=meta)


@mcp.tool
def session_get_messages(
    session_id: str,
    limit_tokens: Optional[int] = None,
) -> dict:
    """Get messages from a session, optionally limited by token count.

    Args:
        session_id: The session UUID
        limit_tokens: Max tokens to return (most recent first). Omit for all.
    """
    return get_client().get_messages(session_id, limit_tokens=limit_tokens)


@mcp.tool
def session_get_token_counts(session_id: str) -> dict:
    """Get total token count for a session.

    Args:
        session_id: The session UUID
    """
    return get_client().get_token_counts(session_id)


@mcp.tool
def session_flush(session_id: str) -> dict:
    """Flush a session - triggers processing of pending messages.

    Args:
        session_id: The session UUID
    """
    return get_client().flush_session(session_id)


@mcp.tool
def session_get_configs(session_id: str) -> dict:
    """Get session configuration.

    Args:
        session_id: The session UUID
    """
    return get_client().get_session_configs(session_id)


@mcp.tool
def session_update_configs(session_id: str, configs: dict) -> dict:
    """Update session configuration.

    Args:
        session_id: The session UUID
        configs: Configuration dict to set
    """
    return get_client().update_session_configs(session_id, configs)


# === Disk (Virtual Filesystem) Operations ===


@mcp.tool
def disk_list() -> dict:
    """List all virtual disks."""
    return get_client().list_disks()


@mcp.tool
def disk_create() -> dict:
    """Create a new virtual disk for file storage."""
    return get_client().create_disk()


@mcp.tool
def disk_write(
    file_path: str,
    content: str,
    disk_id: Optional[str] = None,
    meta: Optional[dict] = None,
) -> dict:
    """Write a file to the virtual disk. Creates or overwrites the file.

    Args:
        file_path: Path in the disk (e.g., "/projects/notes.md")
        content: File content as text
        disk_id: Disk UUID. Uses default disk if omitted.
        meta: Optional metadata dict
    """
    did = disk_id or get_default_disk_id()
    return get_client().upload_artifact(did, file_path, content, meta=meta)


@mcp.tool
def disk_read(file_path: str, disk_id: Optional[str] = None) -> dict:
    """Read a file from the virtual disk.

    Args:
        file_path: Path to read (e.g., "/projects/notes.md")
        disk_id: Disk UUID. Uses default disk if omitted.
    """
    did = disk_id or get_default_disk_id()
    return get_client().get_artifact(did, file_path)


@mcp.tool
def disk_ls(path: str = "/", disk_id: Optional[str] = None) -> dict:
    """List files and directories at a path on the virtual disk.

    Args:
        path: Directory path to list (default: root "/")
        disk_id: Disk UUID. Uses default disk if omitted.
    """
    did = disk_id or get_default_disk_id()
    return get_client().list_artifacts(did, path)


@mcp.tool
def disk_delete(file_path: str, disk_id: Optional[str] = None) -> dict:
    """Delete a file from the virtual disk.

    Args:
        file_path: Path to delete
        disk_id: Disk UUID. Uses default disk if omitted.
    """
    did = disk_id or get_default_disk_id()
    return get_client().delete_artifact(did, file_path)


@mcp.tool
def disk_glob(pattern: str, disk_id: Optional[str] = None) -> dict:
    """Search for files by glob pattern on the virtual disk.

    Args:
        pattern: Glob pattern (e.g., "*.md", "projects/**/*.txt")
        disk_id: Disk UUID. Uses default disk if omitted.
    """
    did = disk_id or get_default_disk_id()
    return get_client().glob_artifacts(did, pattern)


@mcp.tool
def disk_grep(pattern: str, disk_id: Optional[str] = None) -> dict:
    """Search file contents by regex pattern on the virtual disk.

    Args:
        pattern: Regex pattern to search for in file contents
        disk_id: Disk UUID. Uses default disk if omitted.
    """
    did = disk_id or get_default_disk_id()
    return get_client().grep_artifacts(did, pattern)


# === Agent Skills ===


@mcp.tool
def skill_list() -> dict:
    """List all learned agent skills."""
    return get_client().list_skills()


@mcp.tool
def skill_get(skill_id: str) -> dict:
    """Get a specific agent skill by ID.

    Args:
        skill_id: The skill UUID
    """
    return get_client().get_skill(skill_id)


@mcp.tool
def skill_create(name: str, description: str, meta: Optional[dict] = None) -> dict:
    """Create a new agent skill.

    Args:
        name: Skill name
        description: What this skill does
        meta: Optional metadata
    """
    return get_client().create_skill(name, description, meta=meta)


@mcp.tool
def skill_delete(skill_id: str) -> dict:
    """Delete an agent skill.

    Args:
        skill_id: The skill UUID to delete
    """
    return get_client().delete_skill(skill_id)


# === Health ===


@mcp.tool
def health_check() -> dict:
    """Check AContext API health status."""
    return get_client().health()


if __name__ == "__main__":
    mcp.run()

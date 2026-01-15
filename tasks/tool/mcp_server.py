#!/usr/bin/env python3
"""Tasks MCP Server - Fast task management for AI agents."""

from fastmcp import FastMCP
from typing import Optional, List, Dict, Any

mcp = FastMCP("Tasks")
_client = None


def get_client():
    """Lazy initialization - only fails when actually used without config."""
    global _client
    if _client is None:
        from .config import get_api_key
        from .tasks_api import TasksClient

        api_key = get_api_key("NOTION_API_KEY")
        if not api_key:
            raise ValueError(
                "NOTION_API_KEY not configured. "
                "Add to ~/.config/cc-plugins/.env"
            )
        _client = TasksClient()
    return _client


@mcp.tool
def create_task(
    title: str,
    assignee: str,
    priority: str,
    due_date: str,
    task_type: str = "private",
    project: Optional[str] = None,
) -> dict:
    """Create a task in Notion.

    Args:
        title: Task title
        assignee: Person to assign (name or email)
        priority: urgent, high, medium, or low
        due_date: Due date (tomorrow, friday, 2024-01-15, etc.)
        task_type: "private" or "agency"
        project: Project name (required for agency tasks)
    """
    return get_client().create_task(
        title=title,
        assignees=assignee,
        priority=priority,
        due_date=due_date,
        task_type=task_type,
        project=project,
    )


@mcp.tool
def query_tasks(
    task_type: str = "private",
    assignee: Optional[str] = None,
    priority: Optional[str] = None,
    project: Optional[str] = None,
) -> dict:
    """Query tasks with optional filters.

    Args:
        task_type: "private" or "agency"
        assignee: Filter by assignee name
        priority: Filter by priority level
        project: Filter by project name (agency only)
    """
    return {"tasks": get_client().query_tasks(
        task_type=task_type,
        assignee=assignee,
        priority=priority,
        project=project,
    )}


@mcp.tool
def update_task(
    task_id: str,
    title: Optional[str] = None,
    assignee: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None,
    status: Optional[str] = None,
    project: Optional[str] = None,
) -> dict:
    """Update an existing task.

    Args:
        task_id: Notion page ID of the task
        title: New title
        assignee: New assignee
        priority: New priority
        due_date: New due date
        status: New status
        project: New project (agency tasks only)
    """
    return get_client().update_task(
        task_id=task_id,
        title=title,
        assignees=assignee,
        priority=priority,
        due_date=due_date,
        status=status,
        project=project,
    )


@mcp.tool
def get_task(task_id: str) -> dict:
    """Get a single task by ID.

    Args:
        task_id: Notion page ID of the task
    """
    return get_client().get_task(task_id)


@mcp.tool
def list_users() -> List[Dict[str, Any]]:
    """List all users available for task assignment."""
    return get_client().list_users()


@mcp.tool
def list_projects() -> List[Dict[str, Any]]:
    """List all projects available for agency tasks."""
    return get_client().list_projects()


@mcp.tool
def show_config() -> dict:
    """Show current task database configuration."""
    from .user_config import get_private_database_id, get_private_data_source_id, is_configured
    from .tasks_config import AGENCY_TASK_DB, AGENCY_TASK_DATABASE_ID

    return {
        "private_database_configured": is_configured(),
        "private_database_id": get_private_database_id(),
        "private_data_source_id": get_private_data_source_id(),
        "agency_database_id": AGENCY_TASK_DATABASE_ID,
        "agency_data_source_id": AGENCY_TASK_DB.get("data_source_id"),
    }


if __name__ == "__main__":
    mcp.run()

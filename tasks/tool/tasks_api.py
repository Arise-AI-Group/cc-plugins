#!/usr/bin/env python3
"""Tasks API - Notion Task Management.

Create, query, and update tasks in Notion databases with validation.

Usage:
    ./run tool/tasks_api.py users list
    ./run tool/tasks_api.py projects list
    ./run tool/tasks_api.py create private --title "..." --assignee "..." --priority "..." --due "..."
    ./run tool/tasks_api.py create agency --title "..." --assignee "..." --priority "..." --due "..." --project "..."
    ./run tool/tasks_api.py query private [--assignee NAME] [--priority LEVEL]
    ./run tool/tasks_api.py query agency [--assignee NAME] [--priority LEVEL] [--project NAME]
    ./run tool/tasks_api.py update <task_id> [--title "..."] [--assignee "..."] [--priority "..."] [--due "..."] [--status "..."]
    ./run tool/tasks_api.py get <task_id>
    ./run tool/tasks_api.py config show
    ./run tool/tasks_api.py config set-private <database_id>
"""

import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .config import get_api_key
from .tasks_config import (
    AGENCY_TASK_DATABASE_ID,
    AGENCY_TASK_DB,
    PROJECTS_DATABASE_ID,
    PROPERTY_NAMES,
    VALID_PRIORITIES,
    PRIORITY_ALIASES,
)
from .user_config import (
    get_private_database_id,
    get_private_data_source_id,
    set_private_database_ids,
    set_private_database_id,
    is_configured,
)

NOTION_API_KEY = get_api_key("NOTION_API_KEY")


class TaskValidationError(Exception):
    """Raised when task validation fails."""
    pass


class TaskConfigError(Exception):
    """Raised when configuration is missing or invalid."""
    pass


class TasksClient:
    """Client for task management operations."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or NOTION_API_KEY
        if not self.api_key:
            raise ValueError(
                "NOTION_API_KEY not configured. "
                "Set it in ~/.config/cc-plugins/.env"
            )

        from notion_client import Client
        self.client = Client(auth=self.api_key)

        # Cache for user and project lookups
        self._users_cache = None
        self._projects_cache = None

    # === Data Source Operations ===

    def list_database_data_sources(self, database_id: str) -> List[Dict]:
        """List all data sources for a database.

        For single-source databases, returns a list with one data source.
        For multi-source databases (API 2025-09-03+), returns all data sources.

        Args:
            database_id: Database ID to get data sources for

        Returns:
            List of data source objects with 'id' and 'name' keys
        """
        db = self.client.databases.retrieve(database_id=database_id)
        return db.get("data_sources", [])

    def get_primary_data_source_id(self, database_id: str) -> str:
        """Get the primary (first) data source ID for a database.

        For single-source databases, this returns the only data source.
        For multi-source databases, returns the first/default one.

        Args:
            database_id: Database ID

        Returns:
            Data source ID string
        """
        data_sources = self.list_database_data_sources(database_id)
        if data_sources:
            return data_sources[0]["id"]
        # Fallback for backward compatibility with older API responses
        return database_id

    def resolve_data_source_id(
        self,
        database_id: str,
        data_source_id: str = None
    ) -> str:
        """Resolve the data source ID to use for operations.

        If data_source_id is provided, use it directly.
        Otherwise, auto-detect by fetching the primary data source.

        Args:
            database_id: Database ID (container)
            data_source_id: Optional explicit data source ID

        Returns:
            Resolved data source ID
        """
        if data_source_id:
            return data_source_id
        return self.get_primary_data_source_id(database_id)

    # === User Operations ===

    def list_users(self) -> List[Dict]:
        """Get all workspace users (people only, not bots)."""
        if self._users_cache is None:
            response = self.client.users.list()
            self._users_cache = [
                u for u in response.get("results", [])
                if u.get("type") == "person"
            ]
        return self._users_cache

    def find_user_by_name(self, name: str) -> Optional[Dict]:
        """Find user by name (case-insensitive partial match)."""
        users = self.list_users()
        name_lower = name.lower().strip()

        # Exact match first
        for user in users:
            if user.get("name", "").lower() == name_lower:
                return user

        # Partial match (starts with)
        for user in users:
            if user.get("name", "").lower().startswith(name_lower):
                return user

        # Contains match
        for user in users:
            if name_lower in user.get("name", "").lower():
                return user

        return None

    def resolve_assignees(self, names: List[str]) -> List[str]:
        """Resolve user names to Notion user IDs.

        Args:
            names: List of user names to resolve

        Returns:
            List of Notion user IDs

        Raises:
            TaskValidationError: If any user cannot be found
        """
        user_ids = []
        not_found = []

        for name in names:
            user = self.find_user_by_name(name.strip())
            if user:
                user_ids.append(user["id"])
            else:
                not_found.append(name)

        if not_found:
            available = [u.get("name") for u in self.list_users()]
            raise TaskValidationError(
                f"Could not find users: {', '.join(not_found)}. "
                f"Available users: {', '.join(available)}"
            )

        return user_ids

    # === Project Operations ===

    def list_projects(self) -> List[Dict]:
        """Get all projects from the projects database."""
        if self._projects_cache is None:
            if not PROJECTS_DATABASE_ID or PROJECTS_DATABASE_ID.startswith("YOUR_"):
                raise TaskConfigError(
                    "PROJECTS_DATABASE_ID not configured in tasks_config.py"
                )

            response = self.client.data_sources.query(
                data_source_id=PROJECTS_DATABASE_ID,
                page_size=100
            )
            self._projects_cache = response.get("results", [])
        return self._projects_cache

    def _get_page_title(self, page: Dict) -> str:
        """Extract title from a Notion page."""
        props = page.get("properties", {})

        # Try common title property names
        for title_key in ["Name", "Title", "name", "title"]:
            if title_key in props:
                title_prop = props[title_key]
                if "title" in title_prop:
                    title_arr = title_prop["title"]
                    if title_arr:
                        return title_arr[0].get("plain_text", "")

        # Fallback: find any title property
        for prop_name, prop_value in props.items():
            if isinstance(prop_value, dict) and "title" in prop_value:
                title_arr = prop_value["title"]
                if title_arr:
                    return title_arr[0].get("plain_text", "")

        return ""

    def find_project_by_name(self, name: str) -> Optional[Dict]:
        """Find project by name (case-insensitive partial match)."""
        projects = self.list_projects()
        name_lower = name.lower().strip()

        # Exact match first
        for project in projects:
            title = self._get_page_title(project).lower()
            if title == name_lower:
                return project

        # Partial match
        for project in projects:
            title = self._get_page_title(project).lower()
            if name_lower in title:
                return project

        return None

    def resolve_project(self, name: str) -> str:
        """Resolve project name to page ID.

        Args:
            name: Project name to find

        Returns:
            Notion page ID for the project

        Raises:
            TaskValidationError: If project cannot be found
        """
        project = self.find_project_by_name(name)
        if not project:
            available = [self._get_page_title(p) for p in self.list_projects()]
            raise TaskValidationError(
                f"Could not find project: {name}. "
                f"Available projects: {', '.join(available)}"
            )

        return project["id"]

    # === Validation ===

    def normalize_priority(self, priority: str) -> str:
        """Normalize priority input to valid value.

        Args:
            priority: User-provided priority string

        Returns:
            Normalized priority value

        Raises:
            TaskValidationError: If priority is invalid
        """
        priority_lower = priority.lower().strip()

        if priority_lower in PRIORITY_ALIASES:
            return PRIORITY_ALIASES[priority_lower]

        # Check if it matches a valid priority directly
        for valid in VALID_PRIORITIES:
            if valid.lower() == priority_lower:
                return valid

        raise TaskValidationError(
            f"Invalid priority: {priority}. "
            f"Valid values: {', '.join(VALID_PRIORITIES)}"
        )

    def parse_date(self, date_str: str) -> str:
        """Parse date string to ISO format.

        Args:
            date_str: User-provided date string

        Returns:
            ISO format date string (YYYY-MM-DD)

        Raises:
            TaskValidationError: If date cannot be parsed
        """
        date_lower = date_str.lower().strip()
        today = datetime.now().date()

        # Relative dates
        if date_lower == "today":
            return today.isoformat()
        if date_lower == "tomorrow":
            return (today + timedelta(days=1)).isoformat()
        if date_lower in ("next week", "nextweek"):
            return (today + timedelta(days=7)).isoformat()
        if date_lower == "eod":
            return today.isoformat()
        if date_lower == "eow":
            # End of week (Friday)
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0:
                days_until_friday = 7
            return (today + timedelta(days=days_until_friday)).isoformat()

        # Day of week
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if date_lower in days:
            target_day = days.index(date_lower)
            current_day = today.weekday()
            days_ahead = target_day - current_day
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).isoformat()

        # Try parsing as ISO date
        try:
            parsed = datetime.strptime(date_str.strip(), "%Y-%m-%d")
            return parsed.date().isoformat()
        except ValueError:
            pass

        # Try common formats
        formats = [
            "%m/%d/%Y",
            "%m/%d/%y",
            "%d/%m/%Y",
            "%B %d",
            "%B %d, %Y",
            "%b %d",
            "%b %d, %Y",
            "%m-%d-%Y",
            "%m-%d",
        ]
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str.strip(), fmt)
                if parsed.year == 1900:  # No year specified
                    parsed = parsed.replace(year=today.year)
                    # If date is in the past, assume next year
                    if parsed.date() < today:
                        parsed = parsed.replace(year=today.year + 1)
                return parsed.date().isoformat()
            except ValueError:
                continue

        raise TaskValidationError(
            f"Could not parse date: {date_str}. "
            "Use YYYY-MM-DD format or relative terms like 'tomorrow', 'Friday', 'next week'"
        )

    def validate_task(
        self,
        task_type: str,
        title: str,
        assignees: List[str],
        priority: str,
        due_date: str,
        project: Optional[str] = None
    ) -> Dict:
        """Validate and normalize all task fields.

        Args:
            task_type: 'private' or 'agency'
            title: Task title
            assignees: List of assignee names
            priority: Priority level
            due_date: Due date string
            project: Project name (required for agency tasks)

        Returns:
            Dict with validated/normalized values

        Raises:
            TaskValidationError: If validation fails
        """
        errors = []

        # Title
        if not title or not title.strip():
            errors.append("Title is required")

        # Assignees
        user_ids = []
        try:
            user_ids = self.resolve_assignees(assignees)
        except TaskValidationError as e:
            errors.append(str(e))

        # Priority
        normalized_priority = None
        try:
            normalized_priority = self.normalize_priority(priority)
        except TaskValidationError as e:
            errors.append(str(e))

        # Due date
        normalized_date = None
        try:
            normalized_date = self.parse_date(due_date)
        except TaskValidationError as e:
            errors.append(str(e))

        # Project (agency only)
        project_id = None
        if task_type == "agency":
            if not project:
                errors.append("Project is required for agency tasks")
            else:
                try:
                    project_id = self.resolve_project(project)
                except TaskValidationError as e:
                    errors.append(str(e))

        if errors:
            raise TaskValidationError("\n".join(errors))

        return {
            "title": title.strip(),
            "user_ids": user_ids,
            "priority": normalized_priority,
            "due_date": normalized_date,
            "project_id": project_id,
        }

    # === Task Creation ===

    def create_task(
        self,
        task_type: str,
        title: str,
        assignees: List[str],
        priority: str,
        due_date: str,
        project: Optional[str] = None
    ) -> Dict:
        """Create a task in the appropriate database.

        Args:
            task_type: 'private' or 'agency'
            title: Task title
            assignees: List of assignee names
            priority: Priority level
            due_date: Due date string
            project: Project name (required for agency tasks)

        Returns:
            Created Notion page object

        Raises:
            TaskValidationError: If validation fails
            TaskConfigError: If database not configured
        """
        # Validate all fields
        validated = self.validate_task(
            task_type, title, assignees, priority, due_date, project
        )

        # Select database and data_source_id
        if task_type == "agency":
            if not AGENCY_TASK_DATABASE_ID or AGENCY_TASK_DATABASE_ID.startswith("YOUR_"):
                raise TaskConfigError(
                    "AGENCY_TASK_DATABASE_ID not configured in tasks_config.py"
                )
            database_id = AGENCY_TASK_DATABASE_ID
            data_source_id = AGENCY_TASK_DB.get("data_source_id")
        else:
            database_id = get_private_database_id()
            if not database_id:
                raise TaskConfigError(
                    "Private task database not configured. "
                    "Run /tasks-setup or: ./run tool/tasks_api.py config set-private <database_id>"
                )
            data_source_id = get_private_data_source_id()

        # Build properties
        properties = {
            "title": {
                "title": [{"text": {"content": validated["title"]}}]
            },
            PROPERTY_NAMES["assignee"]: {
                "people": [{"id": uid} for uid in validated["user_ids"]]
            },
            PROPERTY_NAMES["priority"]: {
                "select": {"name": validated["priority"]}
            },
            PROPERTY_NAMES["due_date"]: {
                "date": {"start": validated["due_date"]}
            },
        }

        # Add project relation for agency tasks
        if task_type == "agency" and validated["project_id"]:
            properties[PROPERTY_NAMES["project"]] = {
                "relation": [{"id": validated["project_id"]}]
            }

        # Build parent object with data_source_id for multi-source database support
        parent = {"database_id": database_id}
        if data_source_id:
            parent["data_source_id"] = data_source_id

        # Create page with default template
        page = self.client.pages.create(
            parent=parent,
            properties=properties,
            template={"type": "default"}
        )

        return page

    # === Task Get/Update ===

    def get_task(self, task_id: str) -> Dict:
        """Get a single task by ID.

        Args:
            task_id: Notion page ID of the task

        Returns:
            Task page object
        """
        return self.client.pages.retrieve(page_id=task_id)

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        assignees: Optional[List[str]] = None,
        priority: Optional[str] = None,
        due_date: Optional[str] = None,
        status: Optional[str] = None,
        project: Optional[str] = None,
    ) -> Dict:
        """Update an existing task.

        Args:
            task_id: Notion page ID of the task
            title: New task title (optional)
            assignees: New assignee names (optional)
            priority: New priority level (optional)
            due_date: New due date (optional)
            status: New status (optional)
            project: New project name (optional)

        Returns:
            Updated Notion page object
        """
        properties = {}

        if title is not None:
            properties["title"] = {
                "title": [{"text": {"content": title.strip()}}]
            }

        if assignees is not None:
            user_ids = self.resolve_assignees(assignees)
            properties[PROPERTY_NAMES["assignee"]] = {
                "people": [{"id": uid} for uid in user_ids]
            }

        if priority is not None:
            normalized = self.normalize_priority(priority)
            properties[PROPERTY_NAMES["priority"]] = {
                "select": {"name": normalized}
            }

        if due_date is not None:
            parsed_date = self.parse_date(due_date)
            properties[PROPERTY_NAMES["due_date"]] = {
                "date": {"start": parsed_date}
            }

        if status is not None:
            properties[PROPERTY_NAMES["status"]] = {
                "select": {"name": status}
            }

        if project is not None:
            project_id = self.resolve_project(project)
            properties[PROPERTY_NAMES["project"]] = {
                "relation": [{"id": project_id}]
            }

        if not properties:
            raise TaskValidationError("No updates specified")

        return self.client.pages.update(page_id=task_id, properties=properties)

    # === Task Query ===

    def query_tasks(
        self,
        task_type: str,
        assignee: Optional[str] = None,
        priority: Optional[str] = None,
        due_before: Optional[str] = None,
        project: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Query tasks with optional filters.

        Args:
            task_type: 'private' or 'agency'
            assignee: Filter by assignee name
            priority: Filter by priority level
            due_before: Filter by due date (on or before)
            project: Filter by project name (agency only)
            limit: Maximum results to return

        Returns:
            List of matching task pages
        """
        # Select data_source_id for queries
        if task_type == "agency":
            data_source_id = AGENCY_TASK_DB.get("data_source_id")
            if not data_source_id:
                raise TaskConfigError(
                    "AGENCY_TASK_DB not configured in tasks_config.py"
                )
        else:
            data_source_id = get_private_data_source_id()
            if not data_source_id:
                # Fallback: try using database_id (may not work for queries)
                data_source_id = get_private_database_id()
            if not data_source_id:
                raise TaskConfigError(
                    "Private task database not configured. Run /tasks-setup first."
                )

        filters = []

        if assignee:
            user = self.find_user_by_name(assignee)
            if user:
                filters.append({
                    "property": PROPERTY_NAMES["assignee"],
                    "people": {"contains": user["id"]}
                })

        if priority:
            try:
                normalized = self.normalize_priority(priority)
                filters.append({
                    "property": PROPERTY_NAMES["priority"],
                    "select": {"equals": normalized}
                })
            except TaskValidationError:
                pass  # Skip invalid priority filter

        if due_before:
            try:
                date = self.parse_date(due_before)
                filters.append({
                    "property": PROPERTY_NAMES["due_date"],
                    "date": {"on_or_before": date}
                })
            except TaskValidationError:
                pass  # Skip invalid date filter

        if project and task_type == "agency":
            project_page = self.find_project_by_name(project)
            if project_page:
                filters.append({
                    "property": PROPERTY_NAMES["project"],
                    "relation": {"contains": project_page["id"]}
                })

        query_filter = None
        if len(filters) == 1:
            query_filter = filters[0]
        elif len(filters) > 1:
            query_filter = {"and": filters}

        params = {
            "data_source_id": data_source_id,
            "page_size": min(limit, 100)
        }
        if query_filter:
            params["filter"] = query_filter

        response = self.client.data_sources.query(**params)
        return response.get("results", [])


# === CLI Interface ===

def format_user(user: Dict) -> Dict:
    """Format user for display."""
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "email": user.get("person", {}).get("email"),
    }


def format_project(project: Dict, client: TasksClient) -> Dict:
    """Format project for display."""
    return {
        "id": project.get("id"),
        "name": client._get_page_title(project),
    }


def format_task(task: Dict, client: TasksClient) -> Dict:
    """Format task for display."""
    props = task.get("properties", {})

    # Extract title
    title = ""
    title_prop = props.get(PROPERTY_NAMES["title"], {})
    if "title" in title_prop and title_prop["title"]:
        title = title_prop["title"][0].get("plain_text", "")

    # Extract priority
    priority = ""
    priority_prop = props.get(PROPERTY_NAMES["priority"], {})
    if "select" in priority_prop and priority_prop["select"]:
        priority = priority_prop["select"].get("name", "")

    # Extract due date
    due_date = ""
    date_prop = props.get(PROPERTY_NAMES["due_date"], {})
    if "date" in date_prop and date_prop["date"]:
        due_date = date_prop["date"].get("start", "")

    # Extract assignees
    assignees = []
    assignee_prop = props.get(PROPERTY_NAMES["assignee"], {})
    if "people" in assignee_prop:
        for person in assignee_prop["people"]:
            assignees.append(person.get("name", ""))

    return {
        "id": task.get("id"),
        "title": title,
        "priority": priority,
        "due_date": due_date,
        "assignees": assignees,
        "url": task.get("url"),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Task management for Notion databases"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # users command
    users_parser = subparsers.add_parser("users", help="User operations")
    users_sub = users_parser.add_subparsers(dest="users_command")
    users_sub.add_parser("list", help="List workspace users")

    # projects command
    projects_parser = subparsers.add_parser("projects", help="Project operations")
    projects_sub = projects_parser.add_subparsers(dest="projects_command")
    projects_sub.add_parser("list", help="List projects")

    # create command
    create_parser = subparsers.add_parser("create", help="Create a task")
    create_sub = create_parser.add_subparsers(dest="task_type")

    # create private
    create_private = create_sub.add_parser("private", help="Create private task")
    create_private.add_argument("--title", "-t", required=True, help="Task title")
    create_private.add_argument("--assignee", "-a", required=True, help="Assignee name(s), comma-separated")
    create_private.add_argument("--priority", "-p", required=True, help="Priority level")
    create_private.add_argument("--due", "-d", required=True, help="Due date")

    # create agency
    create_agency = create_sub.add_parser("agency", help="Create agency task")
    create_agency.add_argument("--title", "-t", required=True, help="Task title")
    create_agency.add_argument("--assignee", "-a", required=True, help="Assignee name(s), comma-separated")
    create_agency.add_argument("--priority", "-p", required=True, help="Priority level")
    create_agency.add_argument("--due", "-d", required=True, help="Due date")
    create_agency.add_argument("--project", required=True, help="Project name")

    # query command
    query_parser = subparsers.add_parser("query", help="Query tasks")
    query_sub = query_parser.add_subparsers(dest="task_type")

    # query private
    query_private = query_sub.add_parser("private", help="Query private tasks")
    query_private.add_argument("--assignee", "-a", help="Filter by assignee")
    query_private.add_argument("--priority", "-p", help="Filter by priority")
    query_private.add_argument("--due-before", help="Filter by due date")
    query_private.add_argument("--limit", "-n", type=int, default=50, help="Max results")

    # query agency
    query_agency = query_sub.add_parser("agency", help="Query agency tasks")
    query_agency.add_argument("--assignee", "-a", help="Filter by assignee")
    query_agency.add_argument("--priority", "-p", help="Filter by priority")
    query_agency.add_argument("--due-before", help="Filter by due date")
    query_agency.add_argument("--project", help="Filter by project")
    query_agency.add_argument("--limit", "-n", type=int, default=50, help="Max results")

    # get command
    get_parser = subparsers.add_parser("get", help="Get a task by ID")
    get_parser.add_argument("task_id", help="Task page ID")

    # update command
    update_parser = subparsers.add_parser("update", help="Update a task")
    update_parser.add_argument("task_id", help="Task page ID")
    update_parser.add_argument("--title", "-t", help="New task title")
    update_parser.add_argument("--assignee", "-a", help="New assignee(s), comma-separated")
    update_parser.add_argument("--priority", "-p", help="New priority level")
    update_parser.add_argument("--due", "-d", help="New due date")
    update_parser.add_argument("--status", "-s", help="New status")
    update_parser.add_argument("--project", help="New project (agency tasks only)")

    # config command
    config_parser = subparsers.add_parser("config", help="Configuration")
    config_sub = config_parser.add_subparsers(dest="config_command")
    config_sub.add_parser("show", help="Show current configuration")
    set_private = config_sub.add_parser("set-private", help="Set private database ID")
    set_private.add_argument("database_id", help="Notion database ID")

    args = parser.parse_args()

    try:
        # Config commands don't need API client
        if args.command == "config":
            if args.config_command == "show":
                config = {
                    "private_task_database_id": get_private_database_id(),
                    "private_task_data_source_id": get_private_data_source_id(),
                    "agency_task_database_id": AGENCY_TASK_DATABASE_ID,
                    "agency_task_data_source_id": AGENCY_TASK_DB.get("data_source_id"),
                    "projects_database_id": PROJECTS_DATABASE_ID,
                    "configured": is_configured(),
                }
                print(json.dumps(config, indent=2))
                return

            elif args.config_command == "set-private":
                set_private_database_id(args.database_id)
                print(json.dumps({
                    "success": True,
                    "message": f"Private database ID set to: {args.database_id}"
                }, indent=2))
                return

        # Other commands need API client
        client = TasksClient()

        if args.command == "users":
            if args.users_command == "list":
                users = client.list_users()
                print(json.dumps([format_user(u) for u in users], indent=2))

        elif args.command == "projects":
            if args.projects_command == "list":
                projects = client.list_projects()
                print(json.dumps([format_project(p, client) for p in projects], indent=2))

        elif args.command == "create":
            assignees = [a.strip() for a in args.assignee.split(",")]

            if args.task_type == "private":
                page = client.create_task(
                    task_type="private",
                    title=args.title,
                    assignees=assignees,
                    priority=args.priority,
                    due_date=args.due,
                )
            else:
                page = client.create_task(
                    task_type="agency",
                    title=args.title,
                    assignees=assignees,
                    priority=args.priority,
                    due_date=args.due,
                    project=args.project,
                )

            print(json.dumps({
                "success": True,
                "id": page.get("id"),
                "url": page.get("url"),
            }, indent=2))

        elif args.command == "query":
            tasks = client.query_tasks(
                task_type=args.task_type,
                assignee=getattr(args, "assignee", None),
                priority=getattr(args, "priority", None),
                due_before=getattr(args, "due_before", None),
                project=getattr(args, "project", None),
                limit=getattr(args, "limit", 50),
            )
            print(json.dumps([format_task(t, client) for t in tasks], indent=2))

        elif args.command == "get":
            task = client.get_task(args.task_id)
            print(json.dumps(format_task(task, client), indent=2))

        elif args.command == "update":
            assignees = None
            if args.assignee:
                assignees = [a.strip() for a in args.assignee.split(",")]

            page = client.update_task(
                task_id=args.task_id,
                title=args.title,
                assignees=assignees,
                priority=args.priority,
                due_date=args.due,
                status=args.status,
                project=args.project,
            )
            print(json.dumps({
                "success": True,
                "id": page.get("id"),
                "url": page.get("url"),
                "updated": format_task(page, client),
            }, indent=2))

        else:
            parser.print_help()

    except (TaskValidationError, TaskConfigError, ValueError) as e:
        print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {e}"}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

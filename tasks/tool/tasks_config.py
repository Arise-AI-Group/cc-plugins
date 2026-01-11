"""Shared task database configuration.

Agency-wide settings that are the same for all users.
Update these values to match your Notion workspace.
"""

# Agency-wide database IDs (same for all users)
# Notion has two ID types:
#   - database_id: Used for pages.create
#   - data_source_id: Used for data_sources.query
AGENCY_TASK_DB = {
    "database_id": "2d5e7406-6c7d-810e-a1be-c35b71fdf23b",      # For creating pages
    "data_source_id": "2d5e7406-6c7d-8151-bdda-000b46294153",   # For querying
}
PROJECTS_DATABASE_ID = "2d5e7406-6c7d-8167-bb16-000b3ec34789"   # data_source_id for queries

# Legacy single ID (for backward compatibility)
AGENCY_TASK_DATABASE_ID = AGENCY_TASK_DB["database_id"]

# Property names (must match your Notion database schema)
# These should be consistent across all task databases (private and agency)
PROPERTY_NAMES = {
    "title": "Task Name",      # Title property
    "assignee": "Assigned To", # People property
    "priority": "Priority",    # Select property
    "due_date": "Due Date",    # Date property
    "project": "Project",      # Relation property (agency only)
    "status": "Status",        # Optional status property
}

# Valid priority values (must match your Notion select options)
VALID_PRIORITIES = ["Urgent", "High", "Medium", "Low"]

# Priority aliases for flexible input
PRIORITY_ALIASES = {
    "urgent": "Urgent",
    "high": "High",
    "medium": "Medium",
    "med": "Medium",
    "low": "Low",
    "p0": "Urgent",
    "p1": "High",
    "p2": "Medium",
    "p3": "Low",
    "critical": "Urgent",
    "normal": "Medium",
}

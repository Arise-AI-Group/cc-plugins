#!/usr/bin/env python3
"""ActivityWatch MCP Server — comprehensive time tracking analysis for Claude."""

from fastmcp import FastMCP
from typing import Optional, List

mcp = FastMCP("ActivityWatch")
_client = None


def get_client():
    """Lazy initialization of the ActivityWatch API client."""
    global _client
    if _client is None:
        from .aw_api import ActivityWatchAPI
        _client = ActivityWatchAPI()
    return _client


# ---------------------------------------------------------------------------
# Data Exploration
# ---------------------------------------------------------------------------


@mcp.tool
def list_buckets(type_filter: Optional[str] = None) -> list:
    """List all ActivityWatch data buckets with event counts and date ranges.

    Args:
        type_filter: Optional filter by bucket type (e.g., "currentwindow", "afkstatus", "app.editor.activity")
    """
    return get_client().list_buckets(type_filter)


@mcp.tool
def get_bucket_info(bucket_id: str) -> dict:
    """Get detailed info for a bucket including event count, date range, and sample events.

    Args:
        bucket_id: The bucket ID (e.g., "aw-watcher-window_hostname")
    """
    return get_client().get_bucket_info(bucket_id)


@mcp.tool
def get_events(
    bucket_id: str,
    limit: int = 100,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> list:
    """Get raw events from a bucket with optional date filtering.

    Args:
        bucket_id: The bucket ID
        limit: Max events to return (default 100)
        start: Start datetime ISO string (e.g., "2026-02-01T00:00:00")
        end: End datetime ISO string
    """
    return get_client().get_events(bucket_id, limit, start, end)


@mcp.tool
def get_current_activity() -> dict:
    """Get the currently active window and AFK status (requires ActivityWatch server running)."""
    return get_client().get_current_activity()


@mcp.tool
def get_server_info() -> dict:
    """Get ActivityWatch database summary: hostnames, bucket list, total events, DB path."""
    return get_client().get_server_info()


# ---------------------------------------------------------------------------
# Time Analysis
# ---------------------------------------------------------------------------


@mcp.tool
def summarize_day(date: Optional[str] = None) -> dict:
    """Get a complete summary of activity for a single day.

    Returns top apps, top window titles, active/AFK time, and editor activity.

    Args:
        date: Date in ISO format (e.g., "2026-02-07"). Defaults to today.
    """
    return get_client().daily_summary(date)


@mcp.tool
def summarize_range(
    start: str,
    end: str,
    group_by: str = "day",
) -> list:
    """Aggregate active time over a date range, grouped by day or app.

    Args:
        start: Start date (ISO, e.g., "2026-02-01T00:00:00")
        end: End date (ISO)
        group_by: "day" for daily totals, "app" for app totals
    """
    return get_client().range_summary(start, end, group_by)


@mcp.tool
def parallel_activities(start: str, end: str) -> dict:
    """Show parallel work across all data streams (window, VSCode, browser).

    Reveals multitasking: coding while in meetings, browser activity while
    editing, etc. Returns background coding events (VSCode edits while a
    different app was focused), a summary grouped by focused app, and a
    multi-stream timeline interleaving all sources.

    Args:
        start: Start datetime (ISO)
        end: End datetime (ISO)
    """
    return get_client().parallel_activities(start, end)


@mcp.tool
def app_usage(
    days: int = 7,
    app: Optional[str] = None,
) -> dict:
    """Analyze app usage over recent days.

    Without app: returns top apps ranked by time.
    With app: returns daily breakdown and top window titles for that app.

    Args:
        days: Number of days to analyze (default 7)
        app: Optional specific app name to deep-dive into
    """
    return get_client().app_usage(days, app)


@mcp.tool
def productivity_report(start: str, end: str) -> dict:
    """Generate a productivity breakdown categorizing apps as productive/neutral/distracting.

    Categories are configurable via ~/.config/cc-plugins/activitywatch.json.
    Default productive: Code, iTerm2, Terminal, Notion, Cursor.
    Default distracting: Twitter, Reddit, YouTube.

    Args:
        start: Start datetime (ISO)
        end: End datetime (ISO)
    """
    return get_client().productivity_report(start, end)


@mcp.tool
def focus_sessions(
    start: str,
    end: str,
    min_minutes: int = 30,
) -> list:
    """Find deep work/focus sessions — sustained periods of non-AFK activity.

    Returns each session with start/end times, duration, and top apps used.

    Args:
        start: Start datetime (ISO)
        end: End datetime (ISO)
        min_minutes: Minimum session length in minutes (default 30)
    """
    return get_client().find_focus_sessions(start, end, min_minutes)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


@mcp.tool
def run_query(query: str, start: str, end: str) -> list:
    """Execute a raw AQL (ActivityWatch Query Language) query via the REST API.

    Requires ActivityWatch server to be running. Use for advanced analysis
    that benefits from AQL's built-in functions like filter_period_intersect.

    Args:
        query: AQL query string (semicolon-separated statements, ending with RETURN)
        start: Start datetime (ISO)
        end: End datetime (ISO)
    """
    return get_client().run_aql_query(query, start, end)


@mcp.tool
def run_sql(sql: str) -> list:
    """Execute raw SQL against the ActivityWatch SQLite database (read-only).

    Tables: bucketmodel (id, type, client, hostname, created),
            eventmodel (id, bucket_id FK, timestamp, duration, datastr JSON).
    Use json_extract(datastr, '$.key') to query event data fields.

    Args:
        sql: SQL query string
    """
    return get_client().run_sql(sql)


# ---------------------------------------------------------------------------
# Project Tracking
# ---------------------------------------------------------------------------


@mcp.tool
def list_projects() -> list:
    """List all defined projects with their matching rules and manual entry counts."""
    return get_client().list_projects()


@mcp.tool
def get_project_time(project: str, start: str, end: str) -> dict:
    """Calculate total time spent on a project within a date range.

    Combines rule-matched time (from app/title patterns) with manual entries.

    Args:
        project: Project name
        start: Start datetime (ISO)
        end: End datetime (ISO)
    """
    return get_client().get_project_time(project, start, end)


@mcp.tool
def define_project(name: str, rules: str) -> dict:
    """Define a new project with matching rules for automatic time attribution.

    Rules format (JSON string):
    - app_patterns: list of app name substrings (case-insensitive)
    - title_patterns: list of window title substrings
    - title_regex: regex pattern for window titles

    Example: {"app_patterns": ["code", "iterm"], "title_patterns": ["myproject"]}

    Args:
        name: Project name
        rules: JSON string with matching rules
    """
    import json
    return get_client().define_project(name, json.loads(rules))


@mcp.tool
def tag_time(
    start: str,
    end: str,
    project: str,
    notes: Optional[str] = None,
) -> dict:
    """Manually tag a time period to a project.

    Use this for activities that can't be auto-detected from app/title rules
    (e.g., meetings, phone calls, whiteboard sessions).

    Args:
        start: Start datetime (ISO)
        end: End datetime (ISO)
        project: Project name
        notes: Optional description of the activity
    """
    return get_client().tag_time(start, end, project, notes)


@mcp.tool
def delete_project(name: str) -> dict:
    """Remove a project definition and all its rules. Manual entries are also deleted.

    Args:
        name: Project name to delete
    """
    return get_client().delete_project(name)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


@mcp.tool
def daily_report(
    date: Optional[str] = None,
    format: str = "markdown",
) -> str:
    """Generate a shareable daily activity report.

    Includes active time, top apps, top window titles, and editor activity.

    Args:
        date: Date (ISO, default today)
        format: "markdown" or "json"
    """
    result = get_client().generate_daily_report(date, format)
    if isinstance(result, dict):
        import json
        return json.dumps(result, indent=2, default=str)
    return result


@mcp.tool
def weekly_report(
    week_start: Optional[str] = None,
    format: str = "markdown",
) -> str:
    """Generate a weekly summary with daily breakdown and top apps.

    Args:
        week_start: Start of week date (ISO). Defaults to current week's Monday.
        format: "markdown" or "json"
    """
    result = get_client().generate_weekly_report(week_start, format)
    if isinstance(result, dict):
        import json
        return json.dumps(result, indent=2, default=str)
    return result


@mcp.tool
def project_report(
    project: str,
    start: str,
    end: str,
    format: str = "markdown",
) -> str:
    """Generate a project-specific time report suitable for clients or managers.

    Includes rule-matched time breakdown by app and manual entries.

    Args:
        project: Project name
        start: Start datetime (ISO)
        end: End datetime (ISO)
        format: "markdown" or "json"
    """
    result = get_client().generate_project_report(project, start, end, format)
    if isinstance(result, dict):
        import json
        return json.dumps(result, indent=2, default=str)
    return result


@mcp.tool
def visual_report(
    date: Optional[str] = None,
    output_path: Optional[str] = None,
) -> str:
    """Generate a visual HTML activity report with charts, timelines, and parallel tracks.

    Creates a self-contained HTML file with:
    - Hourly timeline with color-coded app segments
    - Donut chart showing app time distribution
    - Parallel swim lanes (window focus, editor, browser)
    - Focus session cards
    - Background coding detection
    - Key activities table

    The report opens in a browser and is saved to Desktop by default.

    Args:
        date: Date (ISO, default today)
        output_path: Optional custom output path (default: ~/Desktop/activity-report-{date}.html)
    """
    path = get_client().generate_html_report(date, output_path)
    return f"Report saved to: {path}"


@mcp.tool
def activity_story(
    date: Optional[str] = None,
    format: str = "markdown",
) -> str:
    """Generate a rich, presentable daily activity report with visual timeline.

    Includes hourly timeline with bars, work blocks, focus sessions,
    parallel work detection, top apps with proportional bars, and key
    activities. Designed for sharing with others or reviewing your day.

    Args:
        date: Date (ISO, default today)
        format: "markdown" or "json"
    """
    result = get_client().generate_activity_story(date, format)
    if isinstance(result, dict):
        import json
        return json.dumps(result, indent=2, default=str)
    return result


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@mcp.tool
def export_range(
    start: str,
    end: str,
    buckets: Optional[List[str]] = None,
    format: str = "json",
) -> str:
    """Export ActivityWatch events for a date range.

    Args:
        start: Start datetime (ISO)
        end: End datetime (ISO)
        buckets: Optional list of bucket IDs to export (default: all)
        format: "json" or "csv"
    """
    import json as json_mod
    result = get_client().export_range(start, end, buckets, format)
    if isinstance(result, list):
        return json_mod.dumps(result, indent=2, default=str)
    return result


@mcp.tool
def export_all() -> dict:
    """Export all ActivityWatch data (all buckets, all events). Can be large."""
    return get_client().export_all()


if __name__ == "__main__":
    mcp.run()

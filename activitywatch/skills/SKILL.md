---
name: activitywatch
description: This skill should be used when the user asks to "analyze my time usage", "show today's activity", "generate time report", "track project time", "what did I work on", "how much time on", "productivity analysis", "time breakdown by app", "export time data", "focus sessions". Provides comprehensive time tracking analysis and reporting via ActivityWatch.
---

# ActivityWatch Time Analysis

## Execution Method
**Always use the MCP tools** (prefixed `mcp__activitywatch__`) for all ActivityWatch operations. Fallback CLI: `tool/aw_api.py`

## Purpose
Analyze time usage from ActivityWatch data, generate reports for sharing, track project time, and identify work patterns. Data comes from a local SQLite database — no API key needed.

## Trigger Phrases
- "Analyze my time usage today/this week"
- "Show today's activity" / "What did I work on?"
- "Generate a daily/weekly time report"
- "How much time did I spend on Code/Slack/Chrome?"
- "Track time for project X"
- "Create a productivity report"
- "Show my app usage breakdown"
- "Find my focus sessions / deep work periods"
- "Export my time data"
- "What apps am I using most?"

## Quick Start

### Today's Summary
Use `summarize_day()` — returns top apps, window titles, active/AFK split, editor activity.

### Weekly Overview
Use `weekly_report()` — generates markdown with daily breakdown and top apps.

### App Deep-Dive
Use `app_usage(days=7, app="Code")` — shows daily time and top window titles for that app.

## Core Operations

### Data Exploration
- `list_buckets()` — discover available data sources (window, AFK, browser, VSCode)
- `get_bucket_info(bucket_id)` — event count, date range, sample events
- `get_events(bucket_id, limit, start, end)` — raw events with date filtering
- `get_current_activity()` — what's active right now (requires AW server running)
- `get_server_info()` — database stats, hostnames, bucket summary

### Time Analysis
- `summarize_day(date)` — full day breakdown (defaults to today)
- `summarize_range(start, end, group_by)` — aggregate by "day" or "app"
- `app_usage(days, app)` — per-app analysis with daily breakdown
- `productivity_report(start, end)` — productive/neutral/distracting categorization
- `focus_sessions(start, end, min_minutes)` — find deep work periods (30min+ by default)

### Project Tracking
- `define_project(name, rules)` — create project with matching rules
  - Rules: `{"app_patterns": ["code"], "title_patterns": ["myproject"], "title_regex": ".*pattern.*"}`
- `get_project_time(project, start, end)` — time from rules + manual entries
- `tag_time(start, end, project, notes)` — manually attribute time
- `list_projects()` / `delete_project(name)`

### Reports
- `daily_report(date, format)` — shareable daily markdown report
- `weekly_report(week_start, format)` — weekly summary with trends
- `project_report(project, start, end, format)` — client/manager-ready

### Raw Queries
- `run_sql(sql)` — direct SQL against the AW SQLite database
  - Tables: `bucketmodel`, `eventmodel` (use `json_extract(datastr, '$.app')`)
- `run_query(query, start, end)` — AQL via REST API

### Export
- `export_range(start, end, buckets, format)` — JSON or CSV export
- `export_all()` — full data export

## Data Sources

ActivityWatch tracks several types of activity in "buckets":

| Bucket Type | Data Fields | Description |
|------------|-------------|-------------|
| `currentwindow` | app, title | Active window tracking |
| `afkstatus` | status | AFK detection (not-afk/afk) |
| `app.editor.activity` | language, file, project | VSCode file editing |
| `web.tab.current` | url, title, tab_count | Browser tab tracking |

Multiple hostnames may exist if the user has used different machines.

## Configuration

**No API key needed** — ActivityWatch runs locally.

Optional settings in `~/.config/cc-plugins/.env`:
```
ACTIVITYWATCH_HOST=localhost
ACTIVITYWATCH_PORT=5600
ACTIVITYWATCH_DB_PATH=/custom/path/to/db
```

Project definitions and productivity categories stored in `~/.config/cc-plugins/activitywatch.json`.

## Common Workflows

### "What did I work on today?"
1. Call `summarize_day()` to get the data
2. Narrate the results: top apps, notable window titles, active time

### "Generate a report for my manager"
1. Call `weekly_report()` for a weekly markdown summary
2. Or `project_report(project, start, end)` for project-specific

### "Track time for client project"
1. `define_project("ClientA", '{"app_patterns": ["code"], "title_patterns": ["clienta"]}')`
2. `get_project_time("ClientA", "2026-02-01T00:00:00", "2026-02-08T00:00:00")`
3. For meetings: `tag_time("2026-02-05T10:00:00", "2026-02-05T11:00:00", "ClientA", "Design review call")`

### "Am I being productive?"
1. `productivity_report(start, end)` — shows productive/neutral/distracting split
2. Customize categories in `~/.config/cc-plugins/activitywatch.json`

## CLI Reference

```bash
./run tool/aw_api.py info                           # DB stats
./run tool/aw_api.py buckets list                    # List buckets
./run tool/aw_api.py analyze today                   # Today's summary
./run tool/aw_api.py analyze app Code --days 14      # Code usage over 2 weeks
./run tool/aw_api.py report daily                    # Daily markdown report
./run tool/aw_api.py report weekly                   # Weekly markdown report
./run tool/aw_api.py project define MyProj --rules '{"app_patterns": ["code"]}'
./run tool/aw_api.py project time MyProj --start 2026-02-01 --end 2026-02-08
./run tool/aw_api.py export range --start 2026-02-01 --end 2026-02-08 --format csv
```

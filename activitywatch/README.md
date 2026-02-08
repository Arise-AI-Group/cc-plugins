# ActivityWatch Plugin

Time tracking analysis, reporting, and project attribution via [ActivityWatch](https://activitywatch.net).

## Features

- **Time Analysis** — App usage, window title breakdown, AFK filtering, focus session detection
- **Project Tracking** — Define projects with matching rules, manually tag time, generate project reports
- **Reports** — Daily and weekly markdown reports suitable for sharing
- **Productivity** — Categorize apps as productive/neutral/distracting with configurable rules
- **Direct SQLite** — Queries the AW database directly for fast, expressive analysis
- **MCP Tools** — 22 tools exposed via FastMCP for Claude Code integration

## Requirements

- [ActivityWatch](https://activitywatch.net) installed and running (or having run at least once)
- Python 3.10+

## Setup

```bash
./setup.sh
```

No API key needed — ActivityWatch runs locally.

## Usage

```bash
# Database info
./run tool/aw_api.py info

# Today's activity
./run tool/aw_api.py analyze today

# App usage over 7 days
./run tool/aw_api.py analyze app Code --days 7

# Daily/weekly reports
./run tool/aw_api.py report daily
./run tool/aw_api.py report weekly

# Project tracking
./run tool/aw_api.py project define MyProject --rules '{"app_patterns": ["code"], "title_patterns": ["myproject"]}'
./run tool/aw_api.py project time MyProject --start 2026-02-01 --end 2026-02-08

# Export
./run tool/aw_api.py export range --start 2026-02-01 --end 2026-02-08 --format csv
```

## Configuration

Optional environment variables in `~/.config/cc-plugins/.env`:

```env
ACTIVITYWATCH_HOST=localhost
ACTIVITYWATCH_PORT=5600
ACTIVITYWATCH_DB_PATH=/custom/path/to/db
```

Project definitions and productivity categories: `~/.config/cc-plugins/activitywatch.json`

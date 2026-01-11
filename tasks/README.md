# Tasks Plugin

Create, query, and update tasks in Notion databases with field validation and interactive prompting.

## Overview

This plugin manages tasks across two Notion databases:
- **Private Tasks**: Your personal task database (per-user)
- **Agency Tasks**: Shared team task database (agency-wide)

All tasks require: **Title**, **Assigned To**, **Priority**, and **Due Date**.
Agency tasks additionally require a **Project** assignment.

## Quick Start

### 1. Install the Plugin
```bash
/plugin install tasks@cc-plugins
```

### 2. Configure Your Private Database
```bash
/tasks-setup
```

### 3. Create a Task
```
Create a high priority task for me to review the proposal by Friday
```

Or use the CLI directly:
```bash
./run tool/tasks_api.py create private \
  --title "Review proposal" \
  --assignee "Your Name" \
  --priority "High" \
  --due "Friday"
```

---

## Setup Guide for New Users

### Prerequisites

1. **NOTION_API_KEY** must be configured in `~/.config/cc-plugins/.env`
   - Run `/skills` from the core plugin to set this up
   - Or get a token from https://www.notion.so/my-integrations

2. **A private task database** in your Notion workspace with these EXACT property names:

| Property | Type | Options |
|----------|------|---------|
| Task Name | Title | - |
| Assigned To | People | - |
| Priority | Select | Urgent, High, Medium, Low |
| Due Date | Date | - |

### Step-by-Step Setup

#### Step 1: Create or Prepare Your Private Database

If you don't have a private task database:
1. Create a new database in your private Notion space
2. Add the required properties with exact names listed above
3. Set up a default template (optional but recommended)

If you have an existing database:
1. Rename properties to match the required names
2. Ensure Priority has options: Urgent, High, Medium, Low

#### Step 2: Connect to Integration

Your database must be shared with the Notion integration:
1. Open your database in Notion
2. Click the **...** menu (top right)
3. Click **Add connections**
4. Select the integration (e.g., "Agentic Workspace")

#### Step 3: Run Setup Command

```bash
/tasks-setup
```

The setup will:
1. Help you find your database
2. Get the required IDs (database_id and data_source_id)
3. Save your configuration
4. Test that everything works

#### Step 4: Verify Setup

```bash
./run tool/tasks_api.py config show
```

Should show `"configured": true`.

---

## Usage

### Creating Tasks

**Via Natural Language (Agent):**
```
Create a task for Sarah to update the documentation by next week
```

```
Add a high priority agency task for the Acme project - fix the login bug
```

The agent will:
- Parse your request
- Ask for any missing required fields
- Create the task in the appropriate database

**Via CLI:**

```bash
# Private task
./run tool/tasks_api.py create private \
  --title "Review proposal" \
  --assignee "Trent" \
  --priority "High" \
  --due "Friday"

# Agency task (requires project)
./run tool/tasks_api.py create agency \
  --title "Fix login bug" \
  --assignee "Sarah" \
  --priority "Urgent" \
  --due "tomorrow" \
  --project "Acme Corp"
```

### Querying Tasks

```bash
# List private tasks
./run tool/tasks_api.py query private --limit 10

# Filter by assignee
./run tool/tasks_api.py query private --assignee "Trent"

# Filter by priority
./run tool/tasks_api.py query agency --priority "High"

# Filter by project
./run tool/tasks_api.py query agency --project "Acme"

# Combine filters
./run tool/tasks_api.py query agency --assignee "Sarah" --priority "Urgent"
```

### Getting a Single Task

```bash
./run tool/tasks_api.py get <task_id>
```

### Updating Tasks

```bash
# Update priority
./run tool/tasks_api.py update <task_id> --priority "Urgent"

# Update due date
./run tool/tasks_api.py update <task_id> --due "tomorrow"

# Update status (mark as done)
./run tool/tasks_api.py update <task_id> --status "Done"

# Reassign task
./run tool/tasks_api.py update <task_id> --assignee "New Person"

# Update multiple fields at once
./run tool/tasks_api.py update <task_id> \
  --title "Updated task title" \
  --priority "High" \
  --due "Friday" \
  --assignee "Sarah"

# Change project (agency tasks)
./run tool/tasks_api.py update <task_id> --project "New Project"
```

### Other Commands

```bash
# List workspace users (for assignee lookup)
./run tool/tasks_api.py users list

# List projects (for agency tasks)
./run tool/tasks_api.py projects list

# Show configuration
./run tool/tasks_api.py config show
```

---

## Required Fields

| Field | Private | Agency | Notes |
|-------|---------|--------|-------|
| Title | Required | Required | Task description |
| Assigned To | Required | Required | Person(s) responsible |
| Priority | Required | Required | Urgent/High/Medium/Low |
| Due Date | Required | Required | When it's due |
| Project | - | **Required** | Links to Projects database |

## Priority Levels

| Level | Aliases | Use When |
|-------|---------|----------|
| Urgent | critical, p0 | Needs immediate attention |
| High | p1 | Important, do soon |
| Medium | med, normal, p2 | Normal priority |
| Low | p3 | Can wait, backlog |

## Date Formats

The plugin accepts flexible date inputs:

| Format | Example |
|--------|---------|
| ISO | `2026-01-15` |
| Relative | `today`, `tomorrow`, `next week` |
| Day names | `monday`, `friday` |
| US format | `01/15/2026`, `1/15` |
| Natural | `January 15`, `Jan 15` |
| Shortcuts | `EOD` (today), `EOW` (Friday) |

---

## Configuration

### Per-User Config (`~/.config/cc-plugins/tasks.json`)

Each user has their own private database configuration:

```json
{
  "private_task_db": {
    "database_id": "xxx-for-creating-tasks",
    "data_source_id": "xxx-for-querying-tasks"
  }
}
```

**Why two IDs?** Notion's API uses different IDs for different operations:
- `database_id` is used by `pages.create` to add new tasks
- `data_source_id` is used by `data_sources.query` to list tasks

### Agency Config (`tool/tasks_config.py`)

Shared configuration for all users (committed to repo):

```python
AGENCY_TASK_DB = {
    "database_id": "xxx",      # For creating tasks
    "data_source_id": "xxx",   # For querying tasks
}
PROJECTS_DATABASE_ID = "xxx"   # Projects database for relations

PROPERTY_NAMES = {
    "title": "Task Name",
    "assignee": "Assigned To",
    "priority": "Priority",
    "due_date": "Due Date",
    "project": "Project",
}

VALID_PRIORITIES = ["Urgent", "High", "Medium", "Low"]
```

---

## Troubleshooting

### "NOTION_API_KEY not configured"
- Run `/skills` from the core plugin
- Or add `NOTION_API_KEY=secret_xxx` to `~/.config/cc-plugins/.env`

### "Could not find database with ID"
- Your database isn't connected to the Notion integration
- In Notion: Open database → ... menu → Add connections → Select integration

### "Task Name is not a property that exists"
- Your database uses different property names
- Rename properties to match: **Task Name**, **Assigned To**, **Priority**, **Due Date**

### "Could not find user: X"
- Run `./run tool/tasks_api.py users list` to see available users
- Use the exact name as shown in the list

### "Could not find project: X"
- Run `./run tool/tasks_api.py projects list` to see available projects
- Use partial name matching (e.g., "Acme" matches "Acme Corp")

### Tasks created but query returns empty
- You may have the wrong ID type configured
- `database_id` is for creates, `data_source_id` is for queries
- Re-run `/tasks-setup` to get both IDs

### Template not applied to new tasks
- Templates are applied asynchronously by Notion
- Refresh the page after a moment
- Ensure a default template is set in your database settings

---

## Database Schema Reference

### Private Task Database

Required properties:

| Property | Type | Configuration |
|----------|------|---------------|
| Task Name | Title | Default title property |
| Assigned To | People | Allow multiple |
| Priority | Select | Options: Urgent, High, Medium, Low |
| Due Date | Date | Date only (no time needed) |
| Status | Status | Optional (Not started, In progress, Done) |

### Agency Task Database

Same as private, plus:

| Property | Type | Configuration |
|----------|------|---------------|
| Project | Relation | Links to Projects database |

---

## For Administrators

### Setting Up a New Team Member

1. Ensure they have access to the Notion workspace
2. Have them create a private task database with the correct schema
3. Share the integration with their database
4. Run `/tasks-setup` to configure

### Changing Agency Database

Update `tool/tasks_config.py` with new IDs:

1. Find the new database's `data_source_id` via search
2. Query the database to get the `database_id` from a page's parent
3. Update both values in `AGENCY_TASK_DB`
4. Commit and push the change

### Adding New Priority Levels

1. Add the option in Notion (to ALL databases)
2. Update `VALID_PRIORITIES` in `tasks_config.py`
3. Optionally add aliases in `PRIORITY_ALIASES`

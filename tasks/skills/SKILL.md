---
name: tasks
description: This skill should be used when the user asks to "create a task", "add to-do", "assign work to", "query my tasks", "update task status", "mark task done", "prioritize my day". Manages Notion tasks with field validation and interactive prompting.
---

# Task Management

## Execution Method
**Use the task-creator agent** for interactive task creation with validation.
**Use Python CLI** for direct operations: `tool/tasks_api.py`

## Purpose
Manage tasks in Notion databases with proper field validation. Supports two database types:
- **Private tasks**: Personal tasks in user's private Notion space
- **Agency tasks**: Team/project tasks in shared agency database

## When to Use This Skill

**Trigger phrases:**
- "Create a task for..."
- "Add a to-do..."
- "Assign X to Y"
- "Make a task for the project"
- "Add this to my tasks"
- "Create an agency task"
- "Track this work item"
- "Add a task with high priority"
- "Show my tasks"
- "What tasks are due today/this week"
- "Update the task..."
- "Mark task as done/complete"
- "Change priority to..."
- "Reassign task to..."
- "Prioritize my day"

## Setup

New users must run `/tasks-setup` before using the plugin.

**Requirements:**
1. `NOTION_API_KEY` in `~/.config/cc-plugins/.env`
2. Private task database with correct property names
3. Database connected to Notion integration

## Quick Reference

### Create Private Task
```bash
cd /Users/trent/Documents/arise/cc-plugins/tasks && ./run tool/tasks_api.py create private \
  --title "Task description" \
  --assignee "Person Name" \
  --priority "High" \
  --due "Friday"
```

### Create Agency Task
```bash
./run tool/tasks_api.py create agency \
  --title "Task description" \
  --assignee "Person Name" \
  --priority "High" \
  --due "Friday" \
  --project "Project Name"
```

### Query Tasks
```bash
# Private tasks
./run tool/tasks_api.py query private --limit 10
./run tool/tasks_api.py query private --assignee "Trent" --priority "High"

# Agency tasks
./run tool/tasks_api.py query agency --project "Acme"
./run tool/tasks_api.py query agency --assignee "Sarah" --priority "Urgent"
```

### Get Single Task
```bash
./run tool/tasks_api.py get <task_id>
```

### Update Task
```bash
# Update priority
./run tool/tasks_api.py update <task_id> --priority "Urgent"

# Update due date
./run tool/tasks_api.py update <task_id> --due "tomorrow"

# Update status
./run tool/tasks_api.py update <task_id> --status "Done"

# Update multiple fields
./run tool/tasks_api.py update <task_id> \
  --priority "High" \
  --due "Friday" \
  --assignee "New Person"
```

### Lookup Commands
```bash
./run tool/tasks_api.py users list      # Available assignees
./run tool/tasks_api.py projects list   # Available projects
./run tool/tasks_api.py config show     # Current configuration
```

## Required Fields

| Field | Private | Agency | Type |
|-------|---------|--------|------|
| Title | Yes | Yes | Text |
| Assigned To | Yes | Yes | People |
| Priority | Yes | Yes | Select |
| Due Date | Yes | Yes | Date |
| Project | No | **Yes** | Relation |

## Priority Levels

- **Urgent** (aliases: critical, p0)
- **High** (aliases: p1)
- **Medium** (aliases: med, normal, p2)
- **Low** (aliases: p3)

## Date Formats

Accepted inputs:
- ISO: `2026-01-15`
- Relative: `today`, `tomorrow`, `next week`
- Day names: `monday`, `friday`
- Common: `01/15/2026`, `January 15`
- Shortcuts: `EOD` (today), `EOW` (Friday)

## Configuration

**Per-user** (`~/.config/cc-plugins/tasks.json`):
```json
{
  "private_task_db": {
    "database_id": "xxx",
    "data_source_id": "xxx"
  }
}
```

**Agency** (`tool/tasks_config.py`):
- `AGENCY_TASK_DB` - Agency database IDs
- `PROJECTS_DATABASE_ID` - Projects database
- `PROPERTY_NAMES` - Property name mapping

## Common Errors

**"NOTION_API_KEY not configured"**
→ Run `/skills` or add key to `~/.config/cc-plugins/.env`

**"Could not find database"**
→ Connect database to integration in Notion

**"Property not found"**
→ Rename database properties to match: Task Name, Assigned To, Priority, Due Date

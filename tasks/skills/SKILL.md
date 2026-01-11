---
name: tasks
description: This skill should be used when the user asks to "create a task", "add to-do", "assign work to", "query my tasks", "update task status", "mark task done", "prioritize my day". Manages Notion tasks with field validation and interactive prompting.
---

# Task Management

## Execution Method
**Use Python CLI** for all operations: `tool/tasks_api.py`

**IMPORTANT: Interactive Prompting Required**
When creating tasks, ALWAYS use `AskUserQuestion` to prompt for missing information before calling the CLI. Never fail with "missing required fields" - instead, ask the user.

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

## Interactive Task Creation Workflow

When a user asks to create a task, follow this workflow:

### Step 1: Extract Information from User Request
Parse what the user provided:
- Title/description
- Assignee (if mentioned)
- Priority (look for: urgent, high, medium, low, critical, p0-p3)
- Due date (look for: dates, tomorrow, Friday, next week, EOD, EOW)
- Task type hints ("personal", "private", "my task" vs "agency", "team", project names)

### Step 2: Prompt for Task Type
**Always ask** whether this is a private or agency task using `AskUserQuestion`:

```
Question: "What type of task is this?"
Options:
- "Private (Recommended)" - Personal task in your private database
- "Agency" - Team/project task in shared agency database
```

Skip this step ONLY if the user explicitly said "agency task" or "private task".

### Step 3: Prompt for Missing Required Fields
For each missing field, use `AskUserQuestion` to gather information:

**Assignee** (if missing):
```
Question: "Who should this task be assigned to?"
Options:
- "Me" - Assign to yourself
- "Someone else" - Specify a different person
```

**Priority** (if missing):
```
Question: "What priority level?"
Options:
- "Medium" - Default for routine tasks
- "Low" - Can be done when time permits
- "High" - Should be done soon
- "Urgent" - Needs immediate attention
```

**Due Date** (if missing - REQUIRED, always prompt):
```
Question: "When is this task due?"
Options:
- "Today" - Due by end of day
- "Tomorrow" - Due tomorrow
- "This week (Friday)" - Due by end of week
- "Next week" - Due in 7 days
```

**Note:** Due date is always required. There is no "no due date" option.

**Project** (for agency tasks only, if missing):
```
Question: "Which project is this task for?"
Options: [List available projects from `./run tool/tasks_api.py projects list`]
```

### Step 4: Create the Task
Once all required fields are gathered, call the CLI with the complete information.

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

**All fields marked "Yes" are mandatory - always prompt for missing fields.**

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

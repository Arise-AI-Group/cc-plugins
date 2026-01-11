---
name: tasks-setup
description: Configure the tasks plugin with your private Notion task database
---

# Tasks Plugin Setup

This command configures your private task database for the tasks plugin.

## Prerequisites

Before running this setup:
1. You must have `NOTION_API_KEY` configured in `~/.config/cc-plugins/.env`
2. You need a private task database in your Notion workspace
3. Your database must use these exact property names:
   - **Task Name** (title) - The task title
   - **Assigned To** (people) - Who's responsible
   - **Priority** (select) - Options: Urgent, High, Medium, Low
   - **Due Date** (date) - When it's due

## Instructions

### Step 1: Check Current Configuration

```bash
cd /Users/trent/Documents/arise/cc-plugins/tasks && ./run tool/tasks_api.py config show
```

If `configured` is already `true`, ask the user if they want to reconfigure.

### Step 2: Verify Notion API Connection

```bash
./run tool/tasks_api.py users list
```

If this fails with "NOTION_API_KEY not configured", tell the user to run `/skills` from the core plugin first, or manually add their key to `~/.config/cc-plugins/.env`.

### Step 3: Find the User's Private Task Database

Search for their database:

```bash
cd /Users/trent/Documents/arise/cc-plugins/notion && ./run tool/notion_api.py search --filter database --limit 30
```

Use AskUserQuestion to ask:
- "What is your private task database called? (e.g., 'Tasks Tracker', 'My Tasks')"

Then search specifically for it:

```bash
./run tool/notion_api.py search "DATABASE_NAME" --filter database
```

The search results will show the **data_source_id** (the ID in parentheses).

### Step 4: Get Both Required IDs

**IMPORTANT**: Notion requires TWO different IDs:
- `data_source_id` - For querying tasks (shown in search results)
- `database_id` - For creating tasks (found in page parent objects)

To get the `database_id`, query the database for one entry:

```bash
./run tool/notion_api.py databases query "DATA_SOURCE_ID" --limit 1
```

Look in the response for:
```json
"parent": {
  "type": "data_source_id",
  "data_source_id": "xxx",
  "database_id": "yyy"   <-- This is what you need
}
```

### Step 5: Verify Integration Access

The user's database MUST be connected to the Notion integration:
1. Open the database in Notion
2. Click the **...** menu (top right)
3. Click **Add connections**
4. Select the integration (usually named "Agentic Workspace" or similar)

If the database isn't connected, creating tasks will fail with "Could not find database".

### Step 6: Save Configuration

Save both IDs to the user's config:

```bash
cd /Users/trent/Documents/arise/cc-plugins/tasks
```

Then use Python to save both IDs:
```python
# In the tasks directory
from tool.user_config import set_private_database_ids
set_private_database_ids(
    database_id="DATABASE_ID_HERE",
    data_source_id="DATA_SOURCE_ID_HERE"
)
```

Or edit `~/.config/cc-plugins/tasks.json` directly:
```json
{
  "private_task_db": {
    "database_id": "xxx-for-creating-tasks",
    "data_source_id": "xxx-for-querying-tasks"
  }
}
```

### Step 7: Test the Setup

Test creating a task:

```bash
./run tool/tasks_api.py create private \
  --title "Test task from setup" \
  --assignee "USER_NAME" \
  --priority "Medium" \
  --due "tomorrow"
```

Test querying tasks:

```bash
./run tool/tasks_api.py query private --limit 3
```

If both work, the setup is complete. Delete the test task in Notion.

### Step 8: Confirm Success

```bash
./run tool/tasks_api.py config show
```

Confirm `configured` is `true` and show the user their configuration.

## Required Database Schema

Your private task database MUST have these properties with EXACT names:

| Property | Type | Options/Notes |
|----------|------|---------------|
| Task Name | Title | The task title |
| Assigned To | People | Person(s) responsible |
| Priority | Select | Urgent, High, Medium, Low |
| Due Date | Date | Due date for the task |

If your database has different property names, you must rename them to match.

## Troubleshooting

**"NOTION_API_KEY not configured"**
- Run `/skills` from the core plugin to configure credentials
- Or add `NOTION_API_KEY=secret_xxx` to `~/.config/cc-plugins/.env`

**"Could not find database with ID"**
- Your database isn't connected to the Notion integration
- In Notion: Database → ... → Add connections → Select integration

**"Task Name is not a property that exists"**
- Your database uses different property names
- Rename properties to match: Task Name, Assigned To, Priority, Due Date

**Tasks created but can't query them**
- You're using the wrong ID type
- Use `database_id` for creates, `data_source_id` for queries
- Re-run setup to get both IDs

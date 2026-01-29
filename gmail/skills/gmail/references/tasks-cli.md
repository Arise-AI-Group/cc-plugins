# Google Tasks CLI Reference

Complete command reference for Google Tasks operations.

## Task Lists

### List All Task Lists
```bash
./run tool/gmail_api.py tasks lists
```

Returns all task lists with IDs and titles.

### Create Task List
```bash
./run tool/gmail_api.py tasks create-list <title>
```

**Example:**
```bash
./run tool/gmail_api.py tasks create-list "Project Alpha"
```

### Delete Task List
```bash
./run tool/gmail_api.py tasks delete-list <tasklist_id>
```

**Warning:** Deletes the list and all tasks within it.

---

## Tasks

### List Tasks
```bash
./run tool/gmail_api.py tasks list [tasklist_id] [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `tasklist_id` | Task list ID (default: @default) |
| `--show-completed` | Include completed tasks |
| `--due-before` | Due before date (YYYY-MM-DD) |
| `--due-after` | Due after date (YYYY-MM-DD) |
| `--limit, -n` | Max results (default: 100) |

**Examples:**
```bash
# List tasks in primary list
./run tool/gmail_api.py tasks list

# List tasks in specific list
./run tool/gmail_api.py tasks list MTIzNDU2Nzg5MA

# Include completed tasks
./run tool/gmail_api.py tasks list @default --show-completed

# Filter by due date
./run tool/gmail_api.py tasks list @default --due-after 2025-01-01 --due-before 2025-01-31
```

### Create Task
```bash
./run tool/gmail_api.py tasks create [tasklist_id] [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `tasklist_id` | Task list ID (default: @default) |
| `--title, -t` | Task title (required) |
| `--notes, -n` | Task notes/description |
| `--due, -d` | Due date (YYYY-MM-DD) |

**Examples:**
```bash
# Simple task
./run tool/gmail_api.py tasks create --title "Review proposal"

# Task with due date
./run tool/gmail_api.py tasks create --title "Send invoice" --due 2025-02-01

# Task with notes
./run tool/gmail_api.py tasks create \
  --title "Call client" \
  --notes "Discuss project timeline and budget" \
  --due 2025-01-15

# Task in specific list
./run tool/gmail_api.py tasks create MTIzNDU2Nzg5MA --title "List-specific task"
```

### Update Task
```bash
./run tool/gmail_api.py tasks update <task_id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--tasklist` | Task list ID (default: @default) |
| `--title, -t` | New title |
| `--notes, -n` | New notes |
| `--due, -d` | New due date |

**Examples:**
```bash
# Update title
./run tool/gmail_api.py tasks update abc123 --title "Updated title"

# Update due date
./run tool/gmail_api.py tasks update abc123 --due 2025-02-15

# Update multiple fields
./run tool/gmail_api.py tasks update abc123 \
  --title "Revised task" \
  --notes "Updated notes" \
  --due 2025-02-20
```

### Complete Task
```bash
./run tool/gmail_api.py tasks complete <task_id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--tasklist` | Task list ID (default: @default) |

**Example:**
```bash
./run tool/gmail_api.py tasks complete abc123
./run tool/gmail_api.py tasks complete abc123 --tasklist MTIzNDU2Nzg5MA
```

### Uncomplete Task
```bash
./run tool/gmail_api.py tasks uncomplete <task_id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--tasklist` | Task list ID (default: @default) |

### Delete Task
```bash
./run tool/gmail_api.py tasks delete <task_id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--tasklist` | Task list ID (default: @default) |

### Clear Completed Tasks
```bash
./run tool/gmail_api.py tasks clear [tasklist_id]
```

Removes all completed tasks from the specified list.

**Example:**
```bash
./run tool/gmail_api.py tasks clear @default
```

---

## Special IDs

### @default
Use `@default` to reference the user's primary task list (usually "My Tasks").

```bash
./run tool/gmail_api.py tasks list @default
./run tool/gmail_api.py tasks create @default --title "New task"
```

---

## Task Object Structure

Tasks returned from the API include:

```json
{
  "id": "MTIzNDU2Nzg5MA",
  "title": "Task title",
  "notes": "Task description",
  "status": "needsAction",
  "due": "2025-02-01T00:00:00.000Z",
  "completed": null,
  "updated": "2025-01-15T10:30:00.000Z",
  "position": "00000000000000000001",
  "parent": null,
  "links": []
}
```

### Status Values
| Status | Description |
|--------|-------------|
| `needsAction` | Task is active/incomplete |
| `completed` | Task is completed |

---

## Common Workflows

### Daily Task Review
```bash
# See today's tasks
./run tool/gmail_api.py tasks list @default --due-before $(date +%Y-%m-%d)

# See upcoming tasks (next 7 days)
./run tool/gmail_api.py tasks list @default \
  --due-after $(date +%Y-%m-%d) \
  --due-before $(date -d "+7 days" +%Y-%m-%d)
```

### Email Follow-up Tasks
```bash
# Create task from email context
./run tool/gmail_api.py tasks create @default \
  --title "Follow up with John about proposal" \
  --notes "Reference: email from 2025-01-15" \
  --due 2025-01-20
```

### Project Task List
```bash
# Create project list
./run tool/gmail_api.py tasks create-list "Project Alpha"

# Add tasks
./run tool/gmail_api.py tasks create <list_id> --title "Phase 1: Research"
./run tool/gmail_api.py tasks create <list_id> --title "Phase 2: Design"
./run tool/gmail_api.py tasks create <list_id> --title "Phase 3: Implementation"
```

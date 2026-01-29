# Task Workflow Examples

Common patterns for managing tasks with Google Tasks integration.

## Daily Task Management

### Morning Task Review
```bash
# List all active tasks
./run tool/gmail_api.py tasks list @default

# List tasks due today
./run tool/gmail_api.py tasks list @default --due-before $(date +%Y-%m-%d)

# List overdue tasks
./run tool/gmail_api.py tasks list @default --due-before $(date -d "yesterday" +%Y-%m-%d)
```

### Quick Task Capture
```bash
# Add task without due date
./run tool/gmail_api.py tasks create --title "Review meeting notes"

# Add task with due date
./run tool/gmail_api.py tasks create --title "Send proposal" --due 2025-02-01

# Add task with notes
./run tool/gmail_api.py tasks create \
  --title "Call John" \
  --notes "Discuss project timeline and Q1 deliverables" \
  --due 2025-01-20
```

### End of Day Cleanup
```bash
# Complete finished tasks
./run tool/gmail_api.py tasks complete <task_id1>
./run tool/gmail_api.py tasks complete <task_id2>

# Clear all completed tasks
./run tool/gmail_api.py tasks clear @default

# Add tasks for tomorrow
./run tool/gmail_api.py tasks create \
  --title "Follow up on yesterday's items" \
  --due $(date -d "tomorrow" +%Y-%m-%d)
```

---

## Email-to-Task Integration

### Create Follow-up Task from Email
```bash
# After reading an important email
./run tool/gmail_api.py messages get <message_id>

# Create a follow-up task
./run tool/gmail_api.py tasks create @default \
  --title "Reply to John's proposal" \
  --notes "Email from: john@company.com
Subject: Q1 Proposal
Key points to address:
- Budget concerns
- Timeline questions" \
  --due 2025-01-18
```

### Track Sent Email Responses
```bash
# After sending an important email
./run tool/gmail_api.py tasks create @default \
  --title "Follow up if no response: Project proposal to Client" \
  --notes "Sent: 2025-01-15
To: client@bigcorp.com
Subject: Project Proposal

Check in 3 days if no response." \
  --due 2025-01-18
```

---

## Project Task Lists

### Create Project Structure
```bash
# Create project task list
./run tool/gmail_api.py tasks create-list "Website Redesign"

# Get the list ID from output, then add tasks
./run tool/gmail_api.py tasks create <list_id> --title "Phase 1: Requirements gathering"
./run tool/gmail_api.py tasks create <list_id> --title "Phase 2: Wireframes"
./run tool/gmail_api.py tasks create <list_id> --title "Phase 3: Design mockups"
./run tool/gmail_api.py tasks create <list_id> --title "Phase 4: Development"
./run tool/gmail_api.py tasks create <list_id> --title "Phase 5: Testing"
./run tool/gmail_api.py tasks create <list_id> --title "Phase 6: Launch"
```

### Track Project Progress
```bash
# List all tasks in project
./run tool/gmail_api.py tasks list <list_id>

# Complete phase
./run tool/gmail_api.py tasks complete <task_id> --tasklist <list_id>

# View completed tasks
./run tool/gmail_api.py tasks list <list_id> --show-completed
```

### Archive Completed Project
```bash
# Clear completed tasks
./run tool/gmail_api.py tasks clear <list_id>

# Or delete the entire list when done
./run tool/gmail_api.py tasks delete-list <list_id>
```

---

## Weekly Planning

### Weekly Review Script
```bash
#!/bin/bash
# Weekly task review

echo "# Weekly Task Review - $(date +%Y-%m-%d)"
echo ""

echo "## Overdue Tasks"
./run tool/gmail_api.py tasks list @default --due-before $(date +%Y-%m-%d) | jq -r '.[] | "- [ ] \(.title) (due: \(.due[:10]))"'

echo ""
echo "## This Week"
./run tool/gmail_api.py tasks list @default \
  --due-after $(date +%Y-%m-%d) \
  --due-before $(date -d "+7 days" +%Y-%m-%d) | jq -r '.[] | "- [ ] \(.title) (due: \(.due[:10]))"'

echo ""
echo "## All Active Tasks"
./run tool/gmail_api.py tasks list @default --limit 50 | jq -r '.[] | "- \(.title)"'
```

### Plan Next Week
```bash
# Add tasks for each day
./run tool/gmail_api.py tasks create --title "Monday: Team standup" --due 2025-01-20
./run tool/gmail_api.py tasks create --title "Tuesday: Client call" --due 2025-01-21
./run tool/gmail_api.py tasks create --title "Wednesday: Review PRs" --due 2025-01-22
./run tool/gmail_api.py tasks create --title "Thursday: Documentation" --due 2025-01-23
./run tool/gmail_api.py tasks create --title "Friday: Weekly report" --due 2025-01-24
```

---

## Multiple Task Lists

### Organize by Context
```bash
# Create context-based lists
./run tool/gmail_api.py tasks create-list "Work"
./run tool/gmail_api.py tasks create-list "Personal"
./run tool/gmail_api.py tasks create-list "Shopping"
./run tool/gmail_api.py tasks create-list "Someday/Maybe"
```

### View All Lists
```bash
# List all task lists
./run tool/gmail_api.py tasks lists

# Check tasks in each list
./run tool/gmail_api.py tasks list <work_list_id>
./run tool/gmail_api.py tasks list <personal_list_id>
```

---

## Integration Patterns

### Combined Email + Task Workflow
```bash
#!/bin/bash
# Process emails and create tasks

# Find emails that need follow-up
FLAGGED=$(./run tool/gmail_api.py messages search "is:starred -label:followed-up" --limit 10)

echo "$FLAGGED" | jq -c '.[]' | while read email; do
  subject=$(echo "$email" | jq -r '.subject')
  from=$(echo "$email" | jq -r '.from')
  msg_id=$(echo "$email" | jq -r '.id')

  # Create follow-up task
  ./run tool/gmail_api.py tasks create @default \
    --title "Follow up: $subject" \
    --notes "From: $from\nMessage ID: $msg_id" \
    --due $(date -d "+3 days" +%Y-%m-%d)

  # Add followed-up label
  ./run tool/gmail_api.py labels apply "$msg_id" --labels "followed-up"
done
```

### Task Report Generation
```bash
#!/bin/bash
# Generate task completion report

echo "# Task Report - Week of $(date +%Y-%m-%d)"
echo ""

# Get completed tasks
echo "## Completed This Week"
./run tool/gmail_api.py tasks list @default --show-completed | \
  jq -r '.[] | select(.status == "completed") | "- \(.title)"'

echo ""
echo "## Still In Progress"
./run tool/gmail_api.py tasks list @default | \
  jq -r '.[] | select(.status == "needsAction") | "- \(.title)"'
```

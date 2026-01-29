---
name: gmail
description: This skill should be used when the user asks to "check my email", "send an email", "search Gmail for", "create a task", "list my tasks", "mark email as read", "export emails to folder", "archive messages", "manage labels". Provides Gmail and Google Tasks management with full email lifecycle support.
---

# Gmail & Google Tasks

## Execution Method

**Always use Python**: `tool/gmail_api.py`

## Purpose

Manage Gmail inbox, send emails, work with drafts, and integrate with Google Tasks. Use this for:
- Reading and searching emails
- Sending emails, replies, and forwards
- Managing labels and organizing inbox
- Creating and managing drafts
- Exporting emails to local files
- Managing Google Tasks for follow-ups

## Trigger Phrases

**Email Reading:**
- "Check my email" / "What's in my inbox"
- "Search Gmail for [query]"
- "Find emails from [sender]"
- "Get messages from the last week"
- "Show me unread emails"

**Email Management:**
- "Archive these emails"
- "Mark as read/unread"
- "Star/unstar this message"
- "Apply label [name] to..."
- "Move to trash"
- "Delete this email"

**Sending:**
- "Send an email to [address]"
- "Reply to this email"
- "Forward this to [address]"
- "Draft an email about..."

**Export:**
- "Save these emails to [folder]"
- "Export thread to markdown"
- "Download attachments"

**Tasks:**
- "Show my tasks"
- "Create a task for [title]"
- "Mark task as complete"
- "Add task with due date"

## Quick Reference

### List & Search Messages
```bash
# List inbox messages
./run tool/gmail_api.py messages list --label INBOX --limit 20

# Search with Gmail query
./run tool/gmail_api.py messages search "from:boss@company.com is:unread"

# Get full message
./run tool/gmail_api.py messages get <message_id>

# Get entire thread
./run tool/gmail_api.py messages thread <thread_id>
```

### Manage Messages
```bash
# Mark as read/unread
./run tool/gmail_api.py messages mark-read <id1> <id2>
./run tool/gmail_api.py messages mark-unread <id>

# Star/archive/trash
./run tool/gmail_api.py messages star <id>
./run tool/gmail_api.py messages archive <id>
./run tool/gmail_api.py messages trash <id>
```

### Labels
```bash
# List labels
./run tool/gmail_api.py labels list

# Create label
./run tool/gmail_api.py labels create "Projects/Active"

# Apply/remove labels
./run tool/gmail_api.py labels apply <msg_id> --labels "Projects/Active" "Important"
./run tool/gmail_api.py labels remove <msg_id> --labels UNREAD
```

### Send Email
```bash
# Send new email
./run tool/gmail_api.py send new --to user@example.com --subject "Hello" --body "Message content"

# Reply to email
./run tool/gmail_api.py send reply <message_id> --body "Thanks for your message"

# Reply all
./run tool/gmail_api.py send reply-all <message_id> --body "Responding to everyone"

# Forward
./run tool/gmail_api.py send forward <message_id> --to another@example.com
```

### Drafts
```bash
# Create draft
./run tool/gmail_api.py drafts create --to user@example.com --subject "Draft" --body "Content"

# List drafts
./run tool/gmail_api.py drafts list

# Send draft
./run tool/gmail_api.py drafts send <draft_id>
```

### Export
```bash
# Export messages to markdown
./run tool/gmail_api.py export messages "from:client@company.com" --output-dir ./emails --format md

# Export thread
./run tool/gmail_api.py export thread <thread_id> --output-dir ./threads

# Export attachments
./run tool/gmail_api.py export attachments <message_id> --output-dir ./attachments
```

### Tasks
```bash
# List task lists
./run tool/gmail_api.py tasks lists

# List tasks
./run tool/gmail_api.py tasks list @default

# Create task with due date
./run tool/gmail_api.py tasks create @default --title "Follow up on proposal" --due 2025-02-01

# Complete task
./run tool/gmail_api.py tasks complete <task_id>
```

## Module Usage

```python
from tool.gmail_api import GmailClient, TasksClient

# Initialize clients
gmail = GmailClient()
tasks = TasksClient()

# List messages
messages = gmail.list_messages(label_ids=['INBOX'], max_results=10)

# Search
results = gmail.search("from:boss@company.com is:unread", max_results=20)

# Get full message
message = gmail.get_message("19c0b9e06a4b60bc")

# Send email
gmail.send_message(
    to=["user@example.com"],
    subject="Hello",
    body="Message content"
)

# Create task
tasks.create_task("@default", title="Follow up", due="2025-02-01")

# Mark task complete
tasks.complete_task("@default", "task_id_here")
```

---

## Gmail Search Query Syntax

Common operators for the `--query` parameter:
- `from:sender@email.com` - From specific sender
- `to:recipient@email.com` - To specific recipient
- `subject:keyword` - Subject contains keyword
- `is:unread` / `is:read` - Read status
- `is:starred` - Starred messages
- `has:attachment` - Has attachments
- `after:2025/01/01` / `before:2025/02/01` - Date range
- `label:work` - Has specific label
- `larger:5M` / `smaller:1M` - Size filters

## OAuth Credentials

On first run, you'll need to authorize the app:
1. Ensure `credentials.json` exists in the plugin directory
2. Run any command to trigger authorization
3. After authorization, `token.json` is saved for future use

**On headless servers**: Run `authenticate.py` interactively via SSH - it will print a URL to visit and prompt for the authorization code.

See [references/oauth-setup.md](references/oauth-setup.md) for detailed setup instructions.

## Additional Resources

- [references/cli-reference.md](references/cli-reference.md) - Complete Gmail CLI commands
- [references/tasks-cli.md](references/tasks-cli.md) - Complete Tasks CLI commands
- [references/oauth-setup.md](references/oauth-setup.md) - OAuth credential setup
- [examples/email-workflows.md](examples/email-workflows.md) - Common email workflows
- [examples/task-workflows.md](examples/task-workflows.md) - Task management patterns

## Edge Cases & Learnings

- **Rate limits**: Gmail has quota of 250 units/user/second. Client auto-retries on 429.
- **Message IDs**: Use full message ID for operations, not thread ID.
- **System labels**: INBOX, SENT, TRASH, SPAM use uppercase IDs.
- **Large attachments**: Downloaded via streaming to handle large files.
- **Permanent delete**: Requires `--force` flag to prevent accidents.
- **Task lists**: Use `@default` for the primary task list.

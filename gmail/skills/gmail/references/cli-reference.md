# Gmail CLI Reference

Complete command reference for Gmail operations.

## Messages

### List Messages
```bash
./run tool/gmail_api.py messages list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--label, -l` | Filter by label (can repeat) |
| `--query, -q` | Gmail search query |
| `--limit, -n` | Max results (default: 20) |
| `--include-spam-trash` | Include spam/trash |

**Examples:**
```bash
# List inbox
./run tool/gmail_api.py messages list --label INBOX

# List unread with limit
./run tool/gmail_api.py messages list --label INBOX --label UNREAD --limit 50

# With query
./run tool/gmail_api.py messages list --query "from:boss@company.com" --limit 10
```

### Search Messages
```bash
./run tool/gmail_api.py messages search <query> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--limit, -n` | Max results (default: 20) |

**Examples:**
```bash
./run tool/gmail_api.py messages search "from:client@company.com has:attachment"
./run tool/gmail_api.py messages search "subject:invoice after:2025/01/01" --limit 100
```

### Get Message
```bash
./run tool/gmail_api.py messages get <message_id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--format` | full, metadata, or raw (default: full) |

### Get Thread
```bash
./run tool/gmail_api.py messages thread <thread_id>
```

### Mark Read/Unread
```bash
./run tool/gmail_api.py messages mark-read <message_ids>...
./run tool/gmail_api.py messages mark-unread <message_ids>...
```

### Star/Unstar
```bash
./run tool/gmail_api.py messages star <message_ids>...
./run tool/gmail_api.py messages unstar <message_ids>...
```

### Archive
```bash
./run tool/gmail_api.py messages archive <message_ids>...
```

### Trash
```bash
./run tool/gmail_api.py messages trash <message_ids>...
```

### Permanently Delete
```bash
./run tool/gmail_api.py messages delete <message_ids>... --force
```

**Warning:** Requires `--force` flag. Cannot be undone.

---

## Labels

### List Labels
```bash
./run tool/gmail_api.py labels list
```

### Create Label
```bash
./run tool/gmail_api.py labels create <name> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--bg-color` | Background color (hex) |
| `--text-color` | Text color (hex) |

**Examples:**
```bash
./run tool/gmail_api.py labels create "Projects/Active"
./run tool/gmail_api.py labels create "Priority" --bg-color "#ff0000" --text-color "#ffffff"
```

### Delete Label
```bash
./run tool/gmail_api.py labels delete <label_id>
```

### Apply Labels
```bash
./run tool/gmail_api.py labels apply <message_id> --labels <labels>...
```

### Remove Labels
```bash
./run tool/gmail_api.py labels remove <message_id> --labels <labels>...
```

---

## Drafts

### List Drafts
```bash
./run tool/gmail_api.py drafts list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--limit, -n` | Max results (default: 20) |

### Create Draft
```bash
./run tool/gmail_api.py drafts create [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--to, -t` | Recipients (required, can repeat) |
| `--subject, -s` | Subject (required) |
| `--body, -b` | Body text |
| `--body-file` | Read body from file |
| `--cc` | CC recipients |
| `--bcc` | BCC recipients |
| `--html` | Body is HTML |
| `--attach` | Files to attach |

**Examples:**
```bash
./run tool/gmail_api.py drafts create \
  --to user@example.com \
  --subject "Meeting notes" \
  --body "Here are the notes..."

./run tool/gmail_api.py drafts create \
  --to user@example.com another@example.com \
  --subject "Report" \
  --body-file ./report.md \
  --attach ./data.xlsx
```

### Update Draft
```bash
./run tool/gmail_api.py drafts update <draft_id> [OPTIONS]
```

### Delete Draft
```bash
./run tool/gmail_api.py drafts delete <draft_id>
```

### Send Draft
```bash
./run tool/gmail_api.py drafts send <draft_id>
```

---

## Send

### Send New Email
```bash
./run tool/gmail_api.py send new [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--to, -t` | Recipients (required) |
| `--subject, -s` | Subject (required) |
| `--body, -b` | Body text |
| `--body-file` | Read body from file |
| `--cc` | CC recipients |
| `--bcc` | BCC recipients |
| `--html` | Body is HTML |
| `--attach` | Files to attach |

### Reply
```bash
./run tool/gmail_api.py send reply <message_id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--body, -b` | Reply body |
| `--body-file` | Read body from file |
| `--html` | Body is HTML |
| `--attach` | Files to attach |

### Reply All
```bash
./run tool/gmail_api.py send reply-all <message_id> [OPTIONS]
```

Same options as reply.

### Forward
```bash
./run tool/gmail_api.py send forward <message_id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--to, -t` | Forward recipients (required) |
| `--body, -b` | Optional body to prepend |

---

## Export

### Export Messages
```bash
./run tool/gmail_api.py export messages <query> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--output-dir, -o` | Output directory (required) |
| `--format, -f` | eml, txt, or md (default: md) |
| `--limit, -n` | Max messages (default: 100) |

**Formats:**
- `eml` - Raw RFC 2822 format (full fidelity)
- `txt` - Plain text with headers
- `md` - Markdown formatted

### Export Thread
```bash
./run tool/gmail_api.py export thread <thread_id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--output-dir, -o` | Output directory (required) |
| `--format, -f` | txt or md (default: md) |

### Export Attachments
```bash
./run tool/gmail_api.py export attachments <message_id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--output-dir, -o` | Output directory (required) |

---

## Gmail Query Syntax

### Basic Operators
| Operator | Description | Example |
|----------|-------------|---------|
| `from:` | Sender | `from:john@example.com` |
| `to:` | Recipient | `to:me@example.com` |
| `subject:` | Subject line | `subject:meeting` |
| `label:` | Has label | `label:work` |

### Status Filters
| Operator | Description |
|----------|-------------|
| `is:unread` | Unread messages |
| `is:read` | Read messages |
| `is:starred` | Starred messages |
| `is:important` | Important messages |
| `is:snoozed` | Snoozed messages |

### Content Filters
| Operator | Description |
|----------|-------------|
| `has:attachment` | Has attachments |
| `has:drive` | Has Google Drive link |
| `has:document` | Has Google Doc |
| `has:spreadsheet` | Has Google Sheet |
| `filename:pdf` | Attachment filename |

### Date Filters
| Operator | Description |
|----------|-------------|
| `after:2025/01/01` | After date |
| `before:2025/02/01` | Before date |
| `older_than:7d` | Older than 7 days |
| `newer_than:1m` | Newer than 1 month |

### Size Filters
| Operator | Description |
|----------|-------------|
| `larger:5M` | Larger than 5MB |
| `smaller:1M` | Smaller than 1MB |

### Combining
```bash
# AND (space)
from:boss@company.com subject:urgent

# OR
from:alice OR from:bob

# NOT
-is:read
-from:newsletter@spam.com

# Grouping
(from:alice OR from:bob) subject:project
```

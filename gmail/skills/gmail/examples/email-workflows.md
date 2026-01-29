# Email Workflow Examples

Common workflow patterns for email automation.

## Inbox Management

### Morning Inbox Review
```bash
# Check unread count
./run tool/gmail_api.py messages list --label INBOX --label UNREAD --limit 1

# List unread messages
./run tool/gmail_api.py messages list --label INBOX --label UNREAD --limit 50

# Read specific message
./run tool/gmail_api.py messages get <message_id>

# Mark as read after reviewing
./run tool/gmail_api.py messages mark-read <id1> <id2> <id3>
```

### Batch Archive Old Messages
```bash
# Find old newsletter messages
./run tool/gmail_api.py messages search "from:newsletter@company.com older_than:30d" --limit 100

# Archive them (use message IDs from search results)
./run tool/gmail_api.py messages archive <id1> <id2> <id3> ...
```

### Find and Label Important Messages
```bash
# Find messages from VIP contacts
./run tool/gmail_api.py messages search "from:ceo@company.com OR from:client@bigcorp.com" --limit 50

# Apply VIP label
./run tool/gmail_api.py labels apply <msg_id> --labels "VIP"
```

---

## Email Composition

### Send Status Update
```bash
./run tool/gmail_api.py send new \
  --to manager@company.com \
  --cc team@company.com \
  --subject "Weekly Status Update" \
  --body "Hi team,

Here's my weekly update:

## Completed
- Finished project X
- Reviewed PRs

## In Progress
- Working on feature Y

## Blockers
- None

Best,
[Name]"
```

### Reply with Context
```bash
# Get original message
./run tool/gmail_api.py messages get <message_id>

# Send reply
./run tool/gmail_api.py send reply <message_id> \
  --body "Thanks for the update. I've reviewed the document and have a few questions:

1. Timeline for phase 2?
2. Budget allocation?

Let me know when you're free to discuss."
```

### Forward with Commentary
```bash
./run tool/gmail_api.py send forward <message_id> \
  --to colleague@company.com \
  --body "FYI - Relevant to our discussion yesterday. What do you think?"
```

---

## Draft Workflows

### Create Draft for Later
```bash
./run tool/gmail_api.py drafts create \
  --to client@company.com \
  --subject "Proposal Follow-up" \
  --body "Draft - Need to add numbers before sending"
```

### Review and Send Drafts
```bash
# List drafts
./run tool/gmail_api.py drafts list

# Review specific draft
./run tool/gmail_api.py messages get <draft_message_id>

# Send when ready
./run tool/gmail_api.py drafts send <draft_id>
```

---

## Export and Backup

### Export Client Correspondence
```bash
# Export all emails from a client
./run tool/gmail_api.py export messages "from:client@bigcorp.com OR to:client@bigcorp.com" \
  --output-dir ./client-emails \
  --format md \
  --limit 500
```

### Export Project Thread
```bash
# Find the thread
./run tool/gmail_api.py messages search "subject:'Project Alpha'"

# Export full thread
./run tool/gmail_api.py export thread <thread_id> \
  --output-dir ./project-threads \
  --format md
```

### Backup Attachments
```bash
# Find messages with attachments
./run tool/gmail_api.py messages search "has:attachment from:vendor@company.com"

# Download attachments
./run tool/gmail_api.py export attachments <message_id> \
  --output-dir ./vendor-invoices
```

---

## Label Organization

### Set Up Project Labels
```bash
# Create label hierarchy
./run tool/gmail_api.py labels create "Projects"
./run tool/gmail_api.py labels create "Projects/Alpha"
./run tool/gmail_api.py labels create "Projects/Beta"
./run tool/gmail_api.py labels create "Projects/Completed"
```

### Organize Messages by Project
```bash
# Find project-related emails
./run tool/gmail_api.py messages search "subject:'Project Alpha'"

# Apply project label
./run tool/gmail_api.py labels apply <msg_id> --labels "Projects/Alpha"
```

### Clean Up Labels
```bash
# List all labels
./run tool/gmail_api.py labels list

# Delete unused label
./run tool/gmail_api.py labels delete <label_id>
```

---

## Automated Processing

### Process and Archive Newsletters
```bash
#!/bin/bash
# Process newsletter emails

# Find recent newsletters
MESSAGES=$(./run tool/gmail_api.py messages search "label:newsletters is:unread" --limit 20)

# Extract message IDs and process
echo "$MESSAGES" | jq -r '.[].id' | while read msg_id; do
  # Export to local archive
  ./run tool/gmail_api.py export messages "rfc822msgid:$msg_id" --output-dir ./newsletter-archive --format md

  # Mark as read and archive
  ./run tool/gmail_api.py messages mark-read "$msg_id"
  ./run tool/gmail_api.py messages archive "$msg_id"
done
```

### Daily Email Summary
```bash
#!/bin/bash
# Generate daily email summary

echo "# Email Summary - $(date +%Y-%m-%d)"
echo ""
echo "## Unread Count"
./run tool/gmail_api.py messages list --label INBOX --label UNREAD --limit 1 | jq 'length'

echo ""
echo "## Priority Messages"
./run tool/gmail_api.py messages search "is:unread (from:boss@company.com OR label:important)" --limit 10 | jq -r '.[] | "- \(.subject) from \(.from)"'

echo ""
echo "## Messages Needing Response"
./run tool/gmail_api.py messages search "is:unread has:question" --limit 10 | jq -r '.[] | "- \(.subject)"'
```

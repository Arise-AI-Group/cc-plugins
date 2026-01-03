---
name: slack
description: Slack channel and message management - create channels, retrieve messages, manage pins, canvases, and user groups. Use when the user asks about slack operations, management, or automation.
---

# Slack Management

## Execution Method
**Always use Python**: `tool/slack_api.py`

Do NOT use n8n MCP tools for Slack operations unless user explicitly requests n8n workflow development.

## Purpose
Manage Slack channels, retrieve messages, and generate AI-powered summaries. Use this for channel lifecycle management, message archival, communication insights, and extracting action items from conversations.

## When to Use This Directive

**Trigger phrases:**
- "Create a Slack channel for..."
- "Archive the old project channel"
- "Update the channel topic/description"
- "Get messages from the last week"
- "Summarize what happened in #channel"
- "What action items came from the discussion?"
- "Pin this message"
- "Set up the channel canvas"
- "List all Slack channels"

## Execution Tools

**Location:**
- `tool/slack_api.py` - Channel and message operations

---

## Channel Operations

### List Channels
```bash
# List all channels
./run tool/slack_api.py channels list

# List only public channels
./run tool/slack_api.py channels list --type public

# List only private channels
./run tool/slack_api.py channels list --type private

# Include archived channels
./run tool/slack_api.py channels list --include-archived
```

### Create Channel
```bash
# Create public channel
./run tool/slack_api.py channels create my-new-channel

# Create private channel
./run tool/slack_api.py channels create my-private-channel --private

# Create with description
./run tool/slack_api.py channels create project-alpha --description "Discussion for Project Alpha Q1 deliverables"
```

### Archive/Unarchive
```bash
# Archive a channel (by ID or name)
./run tool/slack_api.py channels archive C01234567
./run tool/slack_api.py channels archive "#old-project"

# Unarchive a channel
./run tool/slack_api.py channels unarchive C01234567
```

### Get Channel Info
```bash
./run tool/slack_api.py channels info "#general"
./run tool/slack_api.py channels info C01234567
```

### Update Channel Properties
```bash
# Set topic (short text in channel header)
./run tool/slack_api.py channels set-topic "#engineering" "Sprint 23 - Focus on performance"

# Set purpose (longer description)
./run tool/slack_api.py channels set-purpose "#engineering" "Engineering team discussions, code reviews, and technical decisions"
```

---

## Message Operations

### Get Messages
```bash
# Get recent messages (last 100)
./run tool/slack_api.py messages get "#general"

# Get messages from last N days
./run tool/slack_api.py messages get "#general" --days 7

# Get messages from last N hours
./run tool/slack_api.py messages get "#general" --hours 24

# Get messages in date range
./run tool/slack_api.py messages get "#general" --since 2024-01-01 --until 2024-01-31

# Limit number of messages
./run tool/slack_api.py messages get "#general" --days 30 --limit 500

# Output as human-readable text
./run tool/slack_api.py messages get "#general" --days 7 --format text

# Save to file
./run tool/slack_api.py messages get "#general" --days 7 --output .tmp/messages.json
```

### Get Messages from Multiple Channels
```bash
./run tool/slack_api.py messages get-multi "#general" "#engineering" "#product" --days 7
```

---

## Message Summarization

Summarization is done by sharing message output with Claude directly (no separate script needed).

### Workflow
```bash
# Get messages in human-readable format
./run tool/slack_api.py messages get "#general" --days 7 --format text

# Then share the output with Claude and ask for a summary
```

### What to ask Claude for:
- Summary of key discussions
- Action items with owners and due dates
- Upcoming meetings mentioned
- Key decisions made

---

## Pin Operations

```bash
# List pinned items
./run tool/slack_api.py pins list "#general"

# Pin a message (need message timestamp)
./run tool/slack_api.py pins add "#general" 1234567890.123456

# Remove a pin
./run tool/slack_api.py pins remove "#general" 1234567890.123456
```

---

## Canvas Operations

Channel canvases are rich documents attached to channels (also called the "channel description doc" or "first post").

```bash
# Create a canvas with initial content
./run tool/slack_api.py canvas create "#project-alpha" --markdown "# Project Alpha\n\n## Goals\n- Ship by Q2\n- 100 beta users"

# Create canvas from file
./run tool/slack_api.py canvas create "#project-alpha" --markdown-file .tmp/canvas_content.md

# Update existing canvas
./run tool/slack_api.py canvas update "#project-alpha" --markdown-file .tmp/updated_content.md

# Get canvas content
./run tool/slack_api.py canvas get "#project-alpha"
```

---

## Module Usage

```python
from tool.slack_api import SlackClient

client = SlackClient()

# List channels
channels = client.list_channels()

# Create channel
channel = client.create_channel("new-project", description="Project discussions")

# Get messages
messages = client.get_messages("#general", oldest=timestamp, limit=100)

# Resolve channel name to ID
channel_id = client.resolve_channel("#general")  # Returns C01234567
```

---

## Environment Variables

Required in `.env`:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
```

---

## Required Slack App Scopes

When creating the Slack app, add these **Bot Token Scopes**:

| Scope | Purpose |
|-------|---------|
| `channels:manage` | Create/archive public channels |
| `channels:read` | List public channels |
| `channels:history` | Read public channel messages |
| `channels:write.topic` | Set topic/purpose |
| `groups:write` | Manage private channels |
| `groups:read` | List private channels |
| `groups:history` | Read private channel messages |
| `pins:read` | View pinned content |
| `pins:write` | Add/remove pins |
| `canvases:write` | Create/edit canvases |
| `canvases:read` | Read canvas content |
| `users:read` | Resolve user IDs to names |
| `usergroups:write` | Create/manage user groups |
| `usergroups:read` | List user groups |

---

## User Groups (Sidebar Sections)

User groups create shared sidebar sections for team members. Useful for organizing client-related channels.

### List Groups
```bash
./run tool/slack_api.py groups list
./run tool/slack_api.py groups list --include-disabled
```

### Create Group with Channels
```bash
# Create a client group with default channels
./run tool/slack_api.py groups create "Client - Acme" \
  --handle "client-acme" \
  --description "Acme Corp project team" \
  --channels "#acme" "#acme-internal" \
  --users U09FBG483KR U0A0EQ1P6M9 U0A0HQ41MPX
```

### Update Group
```bash
# Add/change default channels
./run tool/slack_api.py groups update S01234567 --channels "#acme" "#acme-internal" "#acme-support"

# Change group name
./run tool/slack_api.py groups update S01234567 --name "Client - Acme Corp"
```

### Manage Members
```bash
# List members
./run tool/slack_api.py groups members S01234567

# Set members (replaces existing)
./run tool/slack_api.py groups members S01234567 --set U09FBG483KR U0A0EQ1P6M9
```

### Disable/Enable Group
```bash
./run tool/slack_api.py groups disable S01234567
./run tool/slack_api.py groups enable S01234567
```

---

## Channel Input Formats

Both channel names and IDs are supported:

```bash
# By name (human-friendly)
./run tool/slack_api.py channels info "#general"
./run tool/slack_api.py channels info "general"

# By ID (programmatic/LLM lookup tables)
./run tool/slack_api.py channels info C01234567
```

---

## Edge Cases & Learnings

- **Rate limits**: Slack API has tier-based rate limits. The client auto-retries on 429 errors with exponential backoff.
- **Channel names**: Must be lowercase, no spaces, max 80 characters. Use hyphens for separation.
- **Private channels**: Bot must be explicitly invited to access private channels. Use `/invite @botname` in Slack.
- **Canvas per channel**: Each channel can only have one canvas. Creating when one exists will error.
- **Message timestamps**: Use full precision timestamps (e.g., `1234567890.123456`) for pinning messages.
- **User IDs**: Messages contain user IDs (U01234567) not names. The summarizer includes these as-is; use `client.get_user_name()` to resolve if needed.
- **Sidebar sections**: Use User Groups with default channels to create shared sidebar sections for team members. Individual sidebar organization is personal per-user.
- **Message pagination**: The API returns max 1000 messages per call. The client handles pagination automatically.

---

## Common Workflows

### Weekly Team Summary
```bash
# Get last week's messages in readable format, then share with Claude for summary
./run tool/slack_api.py messages get "#team" --days 7 --format text
```

### Project Channel Setup
```bash
# Create channel with description
./run tool/slack_api.py channels create "project-beta" --description "Project Beta development"

# Set detailed purpose
./run tool/slack_api.py channels set-purpose "#project-beta" "Development discussions for Project Beta. Sprint planning on Mondays."

# Create channel canvas
./run tool/slack_api.py canvas create "#project-beta" --markdown "# Project Beta\n\n## Team\n- PM: @alice\n- Eng: @bob\n\n## Timeline\n- Kickoff: Jan 15\n- Beta: Mar 1"
```

### Archive Old Projects
```bash
# Get channel info first
./run tool/slack_api.py channels info "#old-project"

# Archive it
./run tool/slack_api.py channels archive "#old-project"
```


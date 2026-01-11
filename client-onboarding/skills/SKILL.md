---
name: client-onboarding
description: This skill should be used when the user asks to "onboard new client", "set up client channels", "create channels for client", "onboard [client name]". Automates Slack channel and resource setup for new clients.
---

# Client Onboarding

## Purpose
Automate the setup of Slack channels and resources for new clients. Creates a standardized workspace with two public channels, templated canvas, welcome message, and team notification.

## When to Use This Directive

**Trigger phrases:**
- "Set up channels for a new client"
- "Onboard [client name]"
- "Create client workspace for..."
- "New client setup"
- "Add a new client to Slack"

## Execution Tools

**Location:**
- `tool/slack_api.py` - Client setup automation (from slack module)

---

## Quick Start

```bash
./run tools/slack_api.py client setup "clientname" --display-name "Client Display Name"
```

This single command:
1. Creates `#clientname` (public, for client communication)
2. Creates `#clientname-internal` (public, for internal discussion - no guests)
3. Clears all system messages from channels (clean slate)
4. Creates a canvas in `#clientname` from template
5. Posts and pins a welcome message
6. Posts notification to `#new-clients` so team can find/join the channels

**Note:** Both channels are public. Team members can join from the notification in `#new-clients`. Guests (clients) can only see channels they're explicitly invited to, so the `-internal` channel remains invisible to them.

---

## Prerequisites

### User Token (Required for Clean Channels)

To delete all system messages (like "joined channel", "set description"), you need a user token:

1. Go to api.slack.com/apps → select your app
2. OAuth & Permissions → User Token Scopes → Add `chat:write`
3. Reinstall app to workspace
4. Copy the user token (xoxp-...) and add to `.env`:
   ```
   SLACK_USER_TOKEN=xoxp-your-token-here
   ```

Without a user token, only bot-posted messages are deleted. System messages will remain.

---

## Command Reference

### Full Command
```bash
./run tools/slack_api.py client setup "<slug>" \
  --display-name "Human Readable Name" \
  --canvas-template templates/client_canvas.md \
  --welcome-template templates/client_welcome.md \
  --notify-channel "#new-clients"
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `slug` | Yes | - | Short name for channels (lowercase, hyphens ok) |
| `--display-name` | No | Titleized slug | Human-readable client name |
| `--canvas-template` | No | `templates/client_canvas.md` | Path to canvas template |
| `--welcome-template` | No | `templates/client_welcome.md` | Path to welcome message template |
| `--notify-channel` | No | `#new-clients` | Channel to post notification about new client |
| `--no-notify` | No | - | Skip posting notification |

### Example Output
```
Setting up client: Acme Corp (acme)
  ✓ Created #acme (C0XXXXXX)
  ✓ Created #acme-internal (C0YYYYYY)
  ✓ Cleared 6 message(s) from channels (all messages)
  ✓ Created canvas in #acme
  ✓ Posted and pinned welcome message
  ✓ Posted notification to #new-clients

Client setup complete!
Channels: #acme, #acme-internal
Next step: Invite client guests to #acme
```

---

## Templates

Templates support variable substitution:
- `{client_name}` - The slug (e.g., "acme")
- `{display_name}` - Human-readable name (e.g., "Acme Corp")
- `{date}` - Today's date (YYYY-MM-DD)

### Canvas Template (`templates/client_canvas.md`)
The canvas serves as the primary reference document for the client channel. Default template includes:
- Quick links section (project management, shared drive, contract)
- Team roster table
- Key dates/milestones
- Notes section

### Welcome Template (`templates/client_welcome.md`)
Brief welcome message that points users to the canvas. Keep it simple - the canvas is the main resource.

---

## Standard Workflow

### 1. Gather Information
Before running the setup command, collect:
- **Client slug**: Short identifier (e.g., "acme", "bigco-2024")
- **Display name**: Full client name (e.g., "Acme Corporation")
- Any special requirements (custom templates)

### 2. Run Setup
```bash
./run tools/slack_api.py client setup "acme" --display-name "Acme Corporation"
```

### 3. Manual Follow-up Steps
After automated setup completes:

1. **Invite client guests**:
   - In `#clientname`, click channel name → Settings → Add people
   - Add clients as single-channel guests

2. **Customize canvas**:
   - Add project management link (Asana, Monday, etc.)
   - Add shared drive link (Google Drive, Dropbox, etc.)
   - Add contract/SOW link
   - Fill in team roster
   - Update key dates

3. **Optional**: Set up Workflow Builder automation for guest welcome (manual in Slack UI)

---

## Why Public Channels?

Both client channels are public because:

1. **Team access**: Members can browse and join without invites
2. **Guest isolation**: Single-channel guests only see channels they're explicitly invited to - they can't browse or discover other channels
3. **Simpler setup**: No invite failures or manual `/invite` steps
4. **Transparency**: Internal team can easily find and join client discussions

The `-internal` channel stays invisible to guests because they're only invited to the main `#clientname` channel.

---

## Edge Cases & Learnings

- **Channel name conflicts**: If `#clientname` already exists, Slack appends characters (e.g., `#clientname-1`). Check for existing channels first if reusing a name.

- **Welcome message timing**: The welcome message is posted after the canvas is created so the canvas appears above it in the channel.

- **Guest limitations**: Single-channel guests can only see the one channel they're invited to. They cannot see other channels, public or private.

- **System message deletion**: Requires user token (xoxp). Bot tokens can only delete the bot's own messages, not Slack system messages like "joined channel".

- **Required scopes**:
  - Bot token: `chat:write`, `channels:manage`, `channels:read`
  - User token: `chat:write` (for deleting system messages)

---

## Troubleshooting

### "missing_scope" error
Add the required scope to your Slack app:
1. Go to api.slack.com/apps
2. Select your app → OAuth & Permissions
3. Add the missing scope under Bot Token Scopes (or User Token Scopes)
4. Reinstall the app to your workspace

### Canvas creation fails
Check that the template file exists at the specified path. The script looks for `templates/client_canvas.md` by default.

### System messages not deleted
You need a user token (xoxp) with `chat:write` scope. Add `SLACK_USER_TOKEN` to your `.env` file.

### Notification not posted
Ensure the `#new-clients` channel exists. Use `--notify-channel` to specify a different channel, or `--no-notify` to skip.

---

## Related Directives

- `runbooks/slack_management.md` - General Slack operations (channel management, messages, pins)


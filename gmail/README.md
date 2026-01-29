# Gmail Plugin

Gmail and Google Tasks management for Claude Code - read emails, send messages, manage labels, drafts, and tasks with full email lifecycle support.

## Installation

```bash
/plugin install gmail@cc-plugins
```

## Features

- **Messages**: List, search, read, archive, trash, delete, mark read/unread, star
- **Labels**: Create, delete, apply, remove labels
- **Drafts**: Create, update, delete, send drafts
- **Send**: New emails, reply, reply-all, forward with attachments
- **Export**: Save emails/threads as .eml, .txt, or .md
- **Tasks**: Google Tasks integration for follow-ups

## Environment Setup

This plugin uses OAuth 2.0 for authentication. No environment variables are required.

### First-Time Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable Gmail API and Tasks API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download the JSON file and save as `credentials.json` in the plugin directory
5. **Run OAuth in terminal** (recommended for security):
   ```bash
   cd /path/to/gmail
   ./.venv/bin/python3 authenticate.py
   ```
   Visit the printed URL, authorize, then paste the code back.

See [skills/gmail/references/oauth-setup.md](skills/gmail/references/oauth-setup.md) for detailed instructions.

## Usage

### Via CLI

```bash
# List inbox messages
./run tool/gmail_api.py messages list --label INBOX --limit 20

# Search emails
./run tool/gmail_api.py messages search "from:boss@company.com is:unread"

# Send email
./run tool/gmail_api.py send new --to user@example.com --subject "Hello" --body "Message"

# List tasks
./run tool/gmail_api.py tasks list @default

# Create task
./run tool/gmail_api.py tasks create --title "Follow up" --due 2025-02-01

# Get help
./run tool/gmail_api.py --help
./run tool/gmail_api.py messages --help
```

### Via Claude Code

Just ask naturally:
- "Check my email"
- "Send an email to john@example.com about the meeting"
- "Search Gmail for messages from the client"
- "Create a task to follow up on the proposal"
- "Export the thread to markdown"

## Skills

This plugin includes the `gmail` skill which auto-triggers on email and task-related requests.

## API Scopes

The plugin requests these OAuth scopes:

| Scope | Purpose |
|-------|---------|
| `gmail.readonly` | Read emails and labels |
| `gmail.modify` | Modify labels, archive, trash |
| `gmail.compose` | Create drafts and send |
| `gmail.labels` | Manage labels |
| `tasks` | Full Google Tasks access |

## License

MIT

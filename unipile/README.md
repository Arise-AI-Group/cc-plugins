# Unipile Plugin

LinkedIn automation via the Unipile unified messaging API. Send messages, manage connections, research profiles, engage with posts/comments, and search LinkedIn.

## Setup

1. Run `./setup.sh` to create the virtual environment
2. Add credentials to `~/.config/cc-plugins/.env`:

```
UNIPILE_API_KEY=your_access_token
UNIPILE_DSN=api27.unipile.com:15796
```

3. Get credentials from [unipile.com](https://unipile.com) — connect your LinkedIn account in the dashboard

## CLI Usage

All commands output JSON to stdout.

```bash
# Find your account ID
./run tool/unipile_api.py accounts list

# Research a prospect
./run tool/unipile_api.py profiles get jane-doe <account_id> --sections '*'

# Send a connection request
./run tool/unipile_api.py connections invite <account_id> jane-doe --message "Hi!"

# Search LinkedIn
./run tool/unipile_api.py search <account_id> "CTO manufacturing" --category people

# Send a message
./run tool/unipile_api.py chats start <account_id> <provider_id> --text "Hello!"

# See all commands
./run tool/unipile_api.py --help
```

## Command Categories

| Category | Commands |
|----------|---------|
| `accounts` | `list`, `get` |
| `profiles` | `me`, `get` |
| `connections` | `list`, `invite`, `cancel`, `sent`, `received` |
| `chats` | `list`, `start`, `messages`, `send` |
| `posts` | `get`, `create`, `comments`, `comment`, `react` |
| `search` | (direct — `search <account_id> <query>`) |
| `webhooks` | `list`, `create`, `delete` |

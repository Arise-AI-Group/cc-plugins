---
name: acontext
description: This skill should be used when the user asks to "save context", "create a session", "store this conversation", "write to disk", "read from disk", "list my files", "check my skills", "search my context". Provides AContext data platform integration for persistent sessions, virtual filesystem, and agent skills.
---

# AContext - Context Data Platform

AContext provides persistent context storage for AI agents across sessions and devices. Three core features: Sessions (conversation memory), Disk (virtual filesystem), and Skills (learned patterns).

## Access Method

### MCP Server (Primary)
All tools are available via MCP. Use them naturally:
- "Save this conversation to a session"
- "Write my project notes to disk"
- "List my saved files"

### API Details
- Base URL: configured via `ACONTEXT_BASE_URL`
- Auth: Bearer token via `ACONTEXT_API_KEY`
- API docs: `{base_url}/swagger/index.html`

## Core Operations

### Sessions
Track conversation threads with persistent message storage.

| Tool | Purpose |
|------|---------|
| `session_list` | List all sessions |
| `session_create` | Create session (optional name) |
| `session_store_message` | Save message (role + content + optional meta) |
| `session_get_messages` | Retrieve messages (optional token limit) |
| `session_get_token_counts` | Get session token usage |
| `session_flush` | Trigger processing of pending messages |
| `session_delete` | Remove session |

Message roles: `user`, `assistant`, `system`

### Disk (Virtual Filesystem)
S3-backed file storage with search capabilities.

| Tool | Purpose |
|------|---------|
| `disk_write` | Write/overwrite file (path + content) |
| `disk_read` | Read file content |
| `disk_ls` | List directory contents |
| `disk_delete` | Remove file |
| `disk_glob` | Search files by pattern (e.g., `*.md`) |
| `disk_grep` | Search file contents by regex |
| `disk_list` | List all disks |
| `disk_create` | Create new disk |

Default disk is auto-selected. Override with `disk_id` parameter.

Recommended structure:
```
/core-context/     - Current focus, active projects
/tasks/            - Task lists, backlogs
/projects/         - Per-project files
/clients/          - Client-specific context
/daily-logs/       - Daily summaries and reviews
```

### Agent Skills
Reusable learned patterns and procedures.

| Tool | Purpose |
|------|---------|
| `skill_list` | List all skills |
| `skill_get` | Get skill details |
| `skill_create` | Create new skill (name + description) |
| `skill_delete` | Remove skill |

### Health
| Tool | Purpose |
|------|---------|
| `health_check` | Verify API connectivity |

## Environment Variables

```
ACONTEXT_BASE_URL=https://acontext-api.40hero.com
ACONTEXT_API_KEY=sk-ac-your-token-here
ACONTEXT_DISK_ID=optional-default-disk-uuid
```

Store in `~/.config/cc-plugins/.env`.

## Common Workflows

### Start of day context load
1. `session_list` to see recent sessions
2. `disk_read` on `/core-context/current-focus.md`
3. `disk_ls` on `/tasks/` for active tasks

### Save conversation context
1. `session_create` with descriptive name
2. `session_store_message` for key exchanges
3. `session_flush` to trigger processing

### Persist working notes
1. `disk_write` to save notes/summaries
2. `disk_grep` to find related content later

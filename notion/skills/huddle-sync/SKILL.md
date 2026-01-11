---
name: huddle-sync
description: This skill should be used when the user asks to "sync huddles to Notion", "update huddle pages", "import Slack huddles", "sync meeting notes from Slack". Syncs Slack huddle notes to Notion Meetings database.
---

# Slack Huddle to Notion Sync

## Purpose

Synchronize Slack huddle meeting notes to the Notion Meetings database. This skill:
- Creates new Notion pages for each huddle
- Updates existing pages with latest notes content
- Automatically maps Slack users to Notion users (by email)
- Preserves formatting, links, and emojis

## Trigger Phrases

- "Sync huddles to Notion"
- "Update the huddle pages"
- "Import Slack huddles"
- "Sync meeting notes from Slack"

## Commands

### Sync New Huddles
Creates NEW Notion pages for all huddles from Slack:
```bash
./run tool/huddle_sync.py sync
```

### Update Existing Huddles
Updates EXISTING Notion pages with latest notes content:
```bash
./run tool/huddle_sync.py update
```

### Refresh Mappings Cache
Rebuilds user/channel mappings from Slack and Notion:
```bash
./run tool/huddle_sync.py refresh
```

### Check Status
Shows cache status and mapped users:
```bash
./run tool/huddle_sync.py status
```

## How It Works

### Automatic Discovery
On first run (or when cache is stale), the tool automatically:
1. Fetches all Slack users and Notion users
2. Matches them by email address
3. Gets all Slack channel names
4. Finds the "Meetings" database in Notion
5. Caches everything to `~/.config/cc-plugins/cache/huddle_mappings.json`

### Cache Management
- Cache auto-refreshes after 7 days
- New users are added when discovered
- Run `refresh` to manually rebuild mappings

## What Gets Synced

### Properties
| Slack Field | Notion Property |
|-------------|-----------------|
| Channel + date | **Name** (title) - e.g., "#dev-main Huddle - 2025-12-21" |
| `date_start` | **Date** |
| `duration_seconds` | **Duration** (minutes) |
| `participant_history` | **Team Attendees** (mapped to Notion users) |
| Notes permalink | **External URL** (links to Slack notes doc) |
| — | **Status** = "Completed" |
| — | **Type** = "Huddle" |
| — | **Source** = "Slack" |

### Page Content
- Huddle notes converted from HTML to Markdown
- Headings, lists, bold/italic preserved
- Links are clickable
- Slack emoji codes converted to actual emojis

## Requirements

Both plugins must be installed and configured:
- `slack` plugin with `SLACK_BOT_TOKEN` and `SLACK_USER_TOKEN`
- `notion` plugin with `NOTION_API_KEY`

The Notion integration must have access to:
- Your Meetings database
- User information (to map attendees)

## Troubleshooting

### "Meetings database not found"
The tool searches Notion for a database with "Meetings" in the name. Either:
- Ensure your database is named "Meetings" (or contains that word)
- Share the database with your Notion integration

### User not mapped
Users are matched by email. If a user isn't mapped:
1. Ensure their Slack and Notion accounts use the same email
2. Run `./run tool/huddle_sync.py refresh` to rebuild mappings

### "Could not find slack plugin"
Both `slack` and `notion` plugins must be installed:
```bash
/plugin install slack@cc-plugins
/plugin install notion@cc-plugins
```

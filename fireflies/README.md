# Fireflies.ai Plugin

Claude Code plugin for Fireflies.ai meeting transcription integration.

## Features

- **List meetings** - View recent meetings with filtering options
- **Get transcripts** - Full transcript text with speaker identification
- **Search meetings** - Find meetings by keyword
- **Action items** - Extract AI-generated action items
- **Summaries** - Get meeting overviews and key points
- **Speaker analytics** - Talk time and participation metrics

## Architecture

This plugin uses a dual-access pattern:

```
┌─────────────────────────────────────────────────────┐
│                   Claude Code                        │
│                                                      │
│  ┌──────────────────┐    ┌──────────────────────┐  │
│  │  MCP (Primary)   │    │  CLI (Fallback)      │  │
│  │                  │    │                       │  │
│  │  mcp-remote      │    │  fireflies_api.py    │  │
│  │       ↓          │    │       ↓               │  │
│  │  api.fireflies   │    │  GraphQL API         │  │
│  │  .ai/mcp         │    │                       │  │
│  └──────────────────┘    └──────────────────────┘  │
└─────────────────────────────────────────────────────┘
              ↑                       ↑
              └───── FIREFLIES_API_KEY ────┘
```

- **MCP Server** (Primary): Auto-loaded by Claude Code, provides natural language access
- **Python CLI** (Fallback): For advanced features like date filtering and speaker analytics

## Setup

1. Get your Fireflies.ai API key from [fireflies.ai/integrations](https://fireflies.ai/integrations)
2. Add to `~/.config/cc-plugins/.env`:
   ```
   FIREFLIES_API_KEY=your-api-key-here
   ```
3. Run setup:
   ```bash
   ./setup.sh
   ```

## MCP Server

The plugin includes an MCP server configuration that connects to Fireflies' official remote MCP endpoint. When the plugin is installed, Claude Code automatically loads the MCP server.

**How it works:**
- `mcp-wrapper` script loads the API key and runs `npx mcp-remote`
- Connects to `https://api.fireflies.ai/mcp` with bearer token auth
- Provides MCP tools directly to Claude Code

**Dependencies:**
- Node.js (for `npx mcp-remote`)
- Network access to `https://api.fireflies.ai/mcp`

## Quick Start

### Via MCP (Natural Language)

After installing the plugin, use natural language:
- "List my recent meetings"
- "Get the transcript for [meeting ID]"
- "What were the action items from [meeting]?"
- "Summarize [meeting]"

### Via CLI

```bash
# List recent meetings
./run tool/fireflies_api.py meetings list --limit 5

# Get meeting summary
./run tool/fireflies_api.py meetings summary TRANSCRIPT_ID

# Get action items
./run tool/fireflies_api.py meetings actions TRANSCRIPT_ID

# Get full transcript
./run tool/fireflies_api.py meetings transcript TRANSCRIPT_ID

# Get speaker analytics (CLI only)
./run tool/fireflies_api.py meetings speakers TRANSCRIPT_ID
```

## MCP vs CLI Features

| Feature | MCP Server | CLI |
|---------|------------|-----|
| List meetings | ✓ | ✓ |
| Get transcript | ✓ | ✓ |
| Get summary | ✓ | ✓ |
| Action items | ✓ | ✓ |
| Search | ✓ | ✓ |
| Speaker analytics | - | ✓ |
| Date filtering | - | ✓ |
| Text output format | - | ✓ |

Use CLI fallback when you need:
- Speaker analytics
- Date range filtering
- Human-readable text output
- Pagination with skip/limit

## Requirements

- Python 3.9+
- Node.js (for MCP server)
- Fireflies.ai Business tier or higher (API access required)

## API Rate Limits

- Free/Pro: 50 requests/day
- Business: 60 requests/minute

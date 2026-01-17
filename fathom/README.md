# Fathom Video Plugin

A Claude Code plugin for integrating with Fathom Video to search meetings, retrieve transcripts, and extract action items.

## Features

- **List Meetings**: View your recent Fathom meetings
- **Search Meetings**: Search across meeting titles and transcripts
- **Get Transcripts**: Retrieve full transcripts with speaker attribution
- **Extract Action Items**: Pull action items from meeting summaries
- **MCP Integration**: Bundled MCP server with automatic API fallback

## Setup

### 1. Get Your Fathom API Key

1. Go to [Fathom Settings](https://fathom.video/settings/api)
2. Generate or copy your API key

### 2. Configure Environment Variable

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export FATHOM_API_KEY="your-api-key-here"
```

Then restart your terminal or run `source ~/.bashrc`.

### 3. Install MCP Server Dependencies

```bash
cd ~/.claude/plugins/fathom/mcp-server
npm install
```

### 4. Verify Configuration

Run the setup command to verify everything is working:

```
/fathom:setup
```

## Commands

| Command | Description |
|---------|-------------|
| `/fathom:meetings [days]` | List recent meetings (optionally specify days to look back) |
| `/fathom:transcript <id>` | Get full transcript for a meeting |
| `/fathom:search <query>` | Search meetings by keyword |
| `/fathom:actions [id]` | Extract action items (uses most recent if no ID) |
| `/fathom:setup` | Verify API configuration |

## Examples

### List Recent Meetings
```
/fathom:meetings
/fathom:meetings 7    # Last 7 days
```

### Search for a Topic
```
/fathom:search "product roadmap"
/fathom:search budget
```

### Get Meeting Details
```
/fathom:transcript abc123
/fathom:actions abc123
```

## Architecture

This plugin uses a hybrid approach:

1. **Primary**: Custom MCP server (`mcp-server/`) provides tools for Claude
2. **Fallback**: Direct API calls via curl when MCP is unavailable

The MCP server implements these tools:
- `list_meetings` - List/filter meetings
- `search_meetings` - Search across meetings
- `get_transcript` - Full transcript with speakers
- `get_summary` - AI-generated summary
- `get_action_items` - Extract action items

## API Reference

Base URL: `https://api.fathom.ai/external/v1`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/meetings` | GET | List meetings |
| `/recordings/{id}/transcript` | GET | Get transcript |
| `/recordings/{id}/summary` | GET | Get summary |

Rate limit: 60 requests/minute

## Troubleshooting

### "FATHOM_API_KEY is not set"
Ensure you've exported the environment variable and restarted your terminal.

### "401 Unauthorized"
Your API key is invalid. Check it at https://fathom.video/settings/api

### MCP Server Not Starting
1. Check that Node.js is installed: `node --version`
2. Install dependencies: `cd mcp-server && npm install`
3. Check for errors: `npx tsx src/index.ts`

## License

MIT

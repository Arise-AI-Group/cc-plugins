---
description: This skill should be used when the user asks to "find meetings", "search Fathom", "get meeting transcript", "extract action items from meeting", "list my meetings", "what was discussed in meeting". Provides Fathom Video integration for meeting search, transcripts, and action item extraction.
---

# Fathom Video Integration

This skill provides integration with Fathom Video for searching meetings, retrieving transcripts, and extracting action items.

## When to Use

Use this skill when the user wants to:
- List or search their Fathom meetings
- Get a transcript from a specific meeting
- Extract action items or summaries from meetings
- Find what was discussed in a particular meeting

## Available MCP Tools

When the Fathom MCP server is available, use these tools:

| Tool | Purpose |
|------|---------|
| `mcp_fathom_list_meetings` | List recent meetings with optional date filtering |
| `mcp_fathom_search_meetings` | Search meetings by keyword or phrase |
| `mcp_fathom_get_transcript` | Get full transcript with speaker attribution |
| `mcp_fathom_get_summary` | Get AI-generated meeting summary |
| `mcp_fathom_get_action_items` | Extract action items from a meeting |

## Usage Patterns

### List Recent Meetings
```
Use mcp_fathom_list_meetings with optional parameters:
- created_after: ISO 8601 date (e.g., "2024-01-01")
- limit: Number of meetings to return (default: 20)
- include_summary: Include summaries in response
```

### Search Meetings
```
Use mcp_fathom_search_meetings with:
- query: The search term to find
- include_transcript: Search within transcripts (default: true)
- limit: Maximum results (default: 10)
```

### Get Transcript
```
Use mcp_fathom_get_transcript with:
- recording_id: The meeting's recording ID (obtained from list/search)
```

### Get Action Items
```
Use mcp_fathom_get_action_items with:
- recording_id: The meeting's recording ID
```

## API Fallback

If MCP tools are unavailable, fall back to direct API calls:

### Base Configuration
- **Base URL**: `https://api.fathom.ai/external/v1`
- **Auth Header**: `X-Api-Key: $FATHOM_API_KEY`
- **Rate Limit**: 60 requests/minute

### Fallback Examples

**List meetings:**
```bash
curl -s "https://api.fathom.ai/external/v1/meetings" \
  -H "X-Api-Key: $FATHOM_API_KEY"
```

**Get transcript:**
```bash
curl -s "https://api.fathom.ai/external/v1/recordings/{recording_id}/transcript" \
  -H "X-Api-Key: $FATHOM_API_KEY"
```

**Get summary:**
```bash
curl -s "https://api.fathom.ai/external/v1/recordings/{recording_id}/summary" \
  -H "X-Api-Key: $FATHOM_API_KEY"
```

## Response Formatting

When presenting meeting data to the user:

1. **Meeting Lists**: Format as a table or bulleted list with title, date, and ID
2. **Transcripts**: Include timestamps and speaker names for context
3. **Action Items**: Present as a checklist format for easy tracking
4. **Summaries**: Include key points and action items sections if available

## Error Handling

- If `FATHOM_API_KEY` is not set, prompt user to configure it
- If API returns 401, the API key is invalid
- If API returns 404, the recording ID doesn't exist
- If API returns 429, rate limit exceeded - wait and retry

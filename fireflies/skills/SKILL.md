---
name: fireflies
description: This skill should be used when the user asks to "list my meetings", "get meeting transcript", "search meeting notes", "find action items from meeting", "who talked most in meeting", "get meeting summary", "show fireflies recordings". Provides Fireflies.ai API integration for meeting transcripts, summaries, action items, and speaker analytics.
---

# Fireflies.ai Integration

Access Fireflies.ai meeting transcription data including transcripts, summaries, action items, and speaker analytics.

## Trigger Phrases

- "list my meetings"
- "get meeting transcript"
- "search meeting notes"
- "find action items from meeting"
- "who talked most in meeting"
- "get meeting summary"
- "show fireflies recordings"
- "get transcript from [meeting name]"

## Access Methods

### MCP Server (Primary)

The Fireflies MCP server is automatically loaded by Claude Code when this plugin is installed. Use natural language to interact:

- "List my recent meetings"
- "Get the transcript for meeting [ID]"
- "Show action items from [meeting]"
- "Summarize [meeting]"
- "Search meetings for [keyword]"

The MCP server provides direct access to Fireflies.ai's API with tools for:
- Listing and filtering meetings
- Getting transcripts and summaries
- Extracting action items
- Searching meeting content

### CLI Fallback

Use the Python CLI when:
- MCP server is disconnected
- Advanced date filtering is needed
- Speaker analytics are required
- Text output format is preferred over JSON
- Pagination with skip/limit is needed

```bash
./run tool/fireflies_api.py [command] [options]
```

## MCP vs CLI Features

| Feature | MCP Server | CLI Fallback |
|---------|------------|--------------|
| List meetings | ✓ | ✓ |
| Get transcript | ✓ | ✓ |
| Get summary | ✓ | ✓ |
| Action items | ✓ | ✓ |
| Search | ✓ | ✓ |
| Speaker analytics | - | ✓ |
| Date filtering | - | ✓ |
| Text output format | - | ✓ |
| Pagination (skip) | - | ✓ |

## CLI Operations

### List Meetings

```bash
# List recent meetings
./run tool/fireflies_api.py meetings list --limit 10

# List my meetings only
./run tool/fireflies_api.py meetings list --mine

# Filter by date range
./run tool/fireflies_api.py meetings list --from-date 2024-01-01 --to-date 2024-01-31

# Filter by host
./run tool/fireflies_api.py meetings list --host user@example.com
```

### Get Meeting Details

```bash
# Get meeting metadata and summary
./run tool/fireflies_api.py meetings get TRANSCRIPT_ID

# Include full transcript sentences
./run tool/fireflies_api.py meetings get TRANSCRIPT_ID --sentences
```

### Search Meetings

```bash
# Search by keyword in title or content
./run tool/fireflies_api.py meetings search "quarterly review"
```

### Get Full Transcript

```bash
# Get formatted transcript with speaker labels
./run tool/fireflies_api.py meetings transcript TRANSCRIPT_ID
```

### Get Summary

```bash
# Get AI-generated summary with key points
./run tool/fireflies_api.py meetings summary TRANSCRIPT_ID
```

### Get Action Items

```bash
# Extract action items from meeting
./run tool/fireflies_api.py meetings actions TRANSCRIPT_ID
```

### Speaker Analytics (CLI Only)

```bash
# Get talk time and word count per speaker
./run tool/fireflies_api.py meetings speakers TRANSCRIPT_ID
```

### User Information

```bash
# Get current user info
./run tool/fireflies_api.py user

# Get specific user
./run tool/fireflies_api.py user USER_ID
```

## Output Formats

CLI commands support `--output-format` (`-o`):
- `json` (default): Structured JSON output
- `text`: Human-readable text

```bash
./run tool/fireflies_api.py -o text meetings list --limit 5
```

## Environment Variables

**Required:**
- `FIREFLIES_API_KEY`: Your Fireflies.ai API key

Set in `~/.config/cc-plugins/.env`:
```
FIREFLIES_API_KEY=your-api-key-here
```

## Common Workflows

### Find Recent Meeting and Get Summary

Via MCP (preferred):
- "List my last 5 meetings"
- "Summarize the [meeting name] meeting"

Via CLI:
```bash
./run tool/fireflies_api.py -o text meetings list --limit 5
./run tool/fireflies_api.py -o text meetings summary TRANSCRIPT_ID
```

### Extract Action Items from Last Week

Via CLI (date filtering):
```bash
./run tool/fireflies_api.py meetings list --from-date 2024-01-08 --to-date 2024-01-15
./run tool/fireflies_api.py -o text meetings actions TRANSCRIPT_ID
```

### Analyze Meeting Participation (CLI Only)

```bash
./run tool/fireflies_api.py -o text meetings speakers TRANSCRIPT_ID
```

## Edge Cases

- **No API key**: Set `FIREFLIES_API_KEY` in environment or `~/.config/cc-plugins/.env`
- **Rate limits**: Free/Pro tier: 50 requests/day, Business tier: 60 requests/minute
- **API access**: Requires Business tier or higher for API access
- **Empty transcripts**: Some meetings may have no transcript data if recording failed
- **Search**: Client-side filtering; fetches recent meetings and filters by keyword
- **MCP disconnected**: Fall back to CLI commands

## Error Handling

The CLI provides clear error messages:
- `Authentication error`: Invalid or missing API key
- `Not found`: Transcript ID doesn't exist
- `Rate limit exceeded`: Too many requests; wait and retry

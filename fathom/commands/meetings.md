---
description: List recent Fathom meetings
arguments:
  - name: days
    description: Number of days to look back (optional, default 30)
    required: false
---

# List Fathom Meetings

List the user's recent Fathom meetings.

## Instructions

1. **Try MCP first**: Attempt to use the `mcp_fathom_list_meetings` tool
   - If `$ARGUMENTS.days` is provided, calculate the `created_after` date
   - Set `limit` to 20 for a reasonable list size

2. **If MCP unavailable**: Fall back to direct API call:
   ```bash
   curl -s "https://api.fathom.ai/external/v1/meetings" \
     -H "X-Api-Key: $FATHOM_API_KEY" | jq '.[:20]'
   ```

3. **Format the response** as a table or list showing:
   - Meeting title
   - Date
   - Duration (if available)
   - Recording ID (for use with other commands)

4. **If FATHOM_API_KEY is not set**, inform the user to run `/fathom:setup`

## Example Output

```
Recent Meetings:

| Title | Date | Duration | ID |
|-------|------|----------|-----|
| Weekly Standup | Jan 15, 2024 | 30m | abc123 |
| Client Call - Acme | Jan 14, 2024 | 45m | def456 |
| Product Review | Jan 12, 2024 | 1h 15m | ghi789 |

Use `/fathom:transcript <id>` to get the full transcript.
Use `/fathom:actions <id>` to extract action items.
```

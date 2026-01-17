---
description: Search Fathom meetings by keyword
arguments:
  - name: query
    description: Search term to find in meetings
    required: true
---

# Search Fathom Meetings

Search across Fathom meetings by keyword or phrase.

## Instructions

1. **Validate input**: Ensure `$ARGUMENTS.query` is provided.

2. **Try MCP first**: Use the `mcp_fathom_search_meetings` tool with:
   - `query`: The search term from `$ARGUMENTS.query`
   - `include_transcript`: true (to search within transcripts)
   - `limit`: 10

3. **If MCP unavailable**: Fall back to direct API call:
   ```bash
   # Fetch meetings and filter locally
   curl -s "https://api.fathom.ai/external/v1/meetings?include_transcript=true" \
     -H "X-Api-Key: $FATHOM_API_KEY" | \
     jq --arg q "$ARGUMENTS.query" '[.[] | select(.title | ascii_downcase | contains($q | ascii_downcase))][:10]'
   ```

4. **Present results** showing:
   - Matching meeting titles
   - Date of meeting
   - Recording ID for further actions
   - Snippet of matching content if available

5. **If no results found**, suggest:
   - Trying different keywords
   - Listing all meetings with `/fathom:meetings`

## Example Output

```
Search results for "API integration":

1. **Client Call - Acme** (Jan 14, 2024)
   ID: def456
   Match: "...discussed the API integration timeline..."

2. **Technical Review** (Jan 10, 2024)
   ID: xyz789
   Match: "...API integration tests are passing..."

Use `/fathom:transcript <id>` to view the full meeting.
```

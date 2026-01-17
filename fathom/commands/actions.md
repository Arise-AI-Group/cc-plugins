---
description: Extract action items from a Fathom meeting
arguments:
  - name: recording_id
    description: The recording ID of the meeting (optional - uses most recent if not provided)
    required: false
---

# Extract Action Items

Extract action items from a Fathom meeting summary.

## Instructions

1. **Determine the meeting**:
   - If `$ARGUMENTS.recording_id` is provided, use it
   - If not provided, first list recent meetings and use the most recent one

2. **Try MCP first**: Use the `mcp_fathom_get_action_items` tool with the `recording_id`

3. **If MCP unavailable**: Fall back to getting the summary and extracting action items:
   ```bash
   curl -s "https://api.fathom.ai/external/v1/recordings/{recording_id}/summary" \
     -H "X-Api-Key: $FATHOM_API_KEY"
   ```
   Then parse the summary for action items, next steps, or to-do items.

4. **Format action items** as a checklist:
   - Use checkbox format `- [ ]` for each item
   - Include assignee if mentioned
   - Include deadline if mentioned

5. **If no action items found**, inform the user and offer:
   - View the full summary
   - View the transcript to manually identify action items

## Example Output

```
## Action Items: Weekly Standup (Jan 15, 2024)

- [ ] Sarah: Submit API integration PR for review
- [ ] Mike: Complete frontend components by Wednesday
- [ ] John: Schedule follow-up meeting with client
- [ ] Team: Review security documentation before Friday

---
Meeting ID: abc123
Use `/fathom:transcript abc123` for full transcript.
```

## No Recording ID Flow

If no recording ID is provided:
1. List the 5 most recent meetings
2. Ask the user which meeting to extract action items from
3. Or automatically use the most recent meeting

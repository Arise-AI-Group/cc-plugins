---
description: Get the full transcript of a Fathom meeting
arguments:
  - name: recording_id
    description: The recording ID of the meeting
    required: true
---

# Get Meeting Transcript

Retrieve the full transcript of a Fathom meeting with speaker attribution.

## Instructions

1. **Validate input**: Ensure `$ARGUMENTS.recording_id` is provided. If not, prompt the user to provide it or suggest running `/fathom:meetings` first.

2. **Try MCP first**: Use the `mcp_fathom_get_transcript` tool with the provided `recording_id`

3. **If MCP unavailable**: Fall back to direct API call:
   ```bash
   curl -s "https://api.fathom.ai/external/v1/recordings/$ARGUMENTS.recording_id/transcript" \
     -H "X-Api-Key: $FATHOM_API_KEY"
   ```

4. **Format the transcript** with:
   - Timestamps (MM:SS format)
   - Speaker names in bold
   - Clear paragraph breaks between speakers

5. **If the transcript is very long**, offer to:
   - Show a summary instead (`/fathom:actions` for action items)
   - Search for specific content within the transcript

## Example Output

```
## Transcript: Weekly Standup (Jan 15, 2024)

[0:00] **John**: Good morning everyone, let's get started with our weekly standup.

[0:15] **Sarah**: I finished the API integration yesterday. Ready for review.

[2:30] **Mike**: I'm working on the frontend components, should be done by tomorrow.

[5:45] **John**: Great progress. Any blockers?
```

## Error Handling

- If recording not found (404): "Meeting not found. Use `/fathom:meetings` to list available meetings."
- If unauthorized (401): "API key invalid. Run `/fathom:setup` to configure."

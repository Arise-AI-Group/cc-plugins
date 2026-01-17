---
description: Verify Fathom API configuration
---

# Fathom Setup

Verify that the Fathom API is properly configured.

## Instructions

1. **Check environment variable**:
   ```bash
   if [ -n "$FATHOM_API_KEY" ]; then
     echo "FATHOM_API_KEY is set"
   else
     echo "FATHOM_API_KEY is NOT set"
   fi
   ```

2. **If API key is set**, test the connection:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" "https://api.fathom.ai/external/v1/meetings?limit=1" \
     -H "X-Api-Key: $FATHOM_API_KEY"
   ```
   - 200: Connection successful
   - 401: Invalid API key
   - Other: Network or API issue

3. **Check MCP server availability**: Look for `mcp_fathom_*` tools in the available tools list.

4. **Report status** to user with clear next steps if needed.

## Example Output (Success)

```
Fathom Configuration Status

Environment:
  FATHOM_API_KEY: Configured

API Connection: Connected
  - Successfully authenticated with Fathom API

MCP Server: Running
  - Tools available: list_meetings, search_meetings, get_transcript, get_summary, get_action_items

Ready to use! Try:
  /fathom:meetings - List recent meetings
  /fathom:search <query> - Search meetings
```

## Example Output (Not Configured)

```
Fathom Configuration Status

Environment:
  FATHOM_API_KEY: Not set

To configure Fathom:

1. Get your API key from https://fathom.video/settings/api

2. Add to your environment:
   export FATHOM_API_KEY="your-api-key-here"

   Or add to your shell profile (~/.bashrc, ~/.zshrc):
   echo 'export FATHOM_API_KEY="your-api-key-here"' >> ~/.bashrc

3. Restart Claude Code to pick up the new environment variable

4. Run /fathom:setup again to verify
```

## Example Output (Invalid Key)

```
Fathom Configuration Status

Environment:
  FATHOM_API_KEY: Configured

API Connection: Failed (401 Unauthorized)
  - The API key appears to be invalid

To fix:
1. Verify your API key at https://fathom.video/settings/api
2. Update FATHOM_API_KEY with the correct value
3. Restart Claude Code and run /fathom:setup again
```

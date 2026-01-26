---
name: n8n
description: This skill should be used when the user asks to "deploy n8n workflow", "list workflows", "activate workflow", "run workflow", "check workflow status", "find n8n node", "search workflow templates", "build new workflow", "what nodes does n8n have". Manages n8n workflows - discover nodes via MCP, deploy/execute via CLI.
---

# n8n Workflow Management

## Two Tools - When to Use Each

This plugin provides TWO integrated tools. Choose the right one:

### n8n-mcp (MCP Server) - Discovery & Building

Use for questions about n8n capabilities and building new workflows:
- "What nodes work with Slack?"
- "Find a template for Google Sheets automation"
- "Help me build a workflow that..."
- "What parameters does the HTTP Request node accept?"
- "Search for webhook examples"

**How to use**: The MCP tools are available directly - just ask questions naturally.

**Capabilities**:
- 1,084+ nodes documented with schemas
- 2,709 workflow templates searchable
- Node property validation
- Community node discovery

### n8n CLI (Python) - Operations & Management

Use for managing deployed workflows on an n8n instance:
- List/get/export workflows
- Deploy workflow JSON files
- Activate/deactivate workflows
- Execute workflows (via webhook)
- View execution history and details

**How to use**: Run commands via `./run tool/n8n_api.py <command>`

## Multi-Instance Support

### IMPORTANT: Session Instance Selection

**Before running ANY CLI operation**, check if multiple n8n instances are configured:

1. Run `./run tool/n8n_api.py profile list`
2. If multiple profiles exist, ASK THE USER which instance to use for this session
3. If only one profile (or none), proceed with the default

**Example prompt to user:**
> "I see you have multiple n8n instances configured:
> - **production**: Main production instance
> - **staging**: Staging/test instance
> - **client-acme**: ACME Corp client instance
>
> Which instance should I use for this session?"

### Switching Instances Mid-Session

```bash
# For CLI operations - use --profile flag
./run tool/n8n_api.py --profile staging list
./run tool/n8n_api.py --profile production activate <id>

# To change the default (affects MCP server on next restart)
./run tool/n8n_api.py profile default staging
```

### Profile Resolution Order

1. `--profile` flag on command -> use that profile
2. `n8n.json` with default_profile -> use default
3. Only one profile in `n8n.json` -> use it automatically
4. No profiles -> fall back to N8N_API_URL/N8N_API_KEY from .env

## Combined Workflow Example

```
1. CHECK INSTANCE: ./run tool/n8n_api.py profile list
   -> If multiple, ask user which to use
2. DISCOVER (n8n-mcp): "Find nodes that integrate with Google Sheets"
3. TEMPLATE (n8n-mcp): "Search for sheet to Slack notification templates"
4. BUILD (n8n-mcp): "Help build a workflow that reads sheet and posts to Slack"
5. SAVE: Write JSON to workflows/sheet-slack.json
6. DEPLOY (CLI): ./run tool/n8n_api.py create workflows/sheet-slack.json
7. ACTIVATE (CLI): ./run tool/n8n_api.py activate <id>
8. TEST (CLI): ./run tool/n8n_api.py execute <id>
9. MONITOR (CLI): ./run tool/n8n_api.py executions <id>
```

## Profile Management Commands

```bash
# List all configured instances
./run tool/n8n_api.py profile list

# Add a new instance
./run tool/n8n_api.py profile add client-foo \
  --url https://n8n.client-foo.com \
  --api-key-env N8N_CLIENTFOO_API_KEY \
  --description "Client Foo's n8n instance"

# Set default instance
./run tool/n8n_api.py profile default production

# Remove an instance
./run tool/n8n_api.py profile remove old-instance
```

## CLI Commands Reference

### Workflow Operations

```bash
# List all workflows
./run tool/n8n_api.py list

# Get workflow JSON (for inspection/debugging)
./run tool/n8n_api.py get <workflow_id>

# Get workflow info (triggers, webhook URLs)
./run tool/n8n_api.py info <workflow_id>

# Deploy new workflow from local file
./run tool/n8n_api.py create workflows/my_workflow.json

# Update existing workflow
./run tool/n8n_api.py update <workflow_id> workflows/my_workflow.json

# Activate/deactivate workflow
./run tool/n8n_api.py activate <workflow_id>
./run tool/n8n_api.py deactivate <workflow_id>

# Execute workflow via webhook (requires webhook trigger + active workflow)
./run tool/n8n_api.py execute <workflow_id> [input_json]

# Export workflow to local file
./run tool/n8n_api.py export <workflow_id> workflows/exported.json

# Delete workflow (with confirmation)
./run tool/n8n_api.py delete <workflow_id>
```

## Execution Monitoring (CLI Only)

n8n-mcp does NOT provide execution data - use CLI for all monitoring.

### View Execution History

```bash
# Last 20 executions for a workflow
./run tool/n8n_api.py executions <workflow_id>

# Custom limit
./run tool/n8n_api.py executions <workflow_id> 50

# With profile
./run tool/n8n_api.py --profile staging executions <workflow_id>
```

Output shows: execution ID, status (success/error/running), timestamps

### Get Execution Details

```bash
# Summary view
./run tool/n8n_api.py execution <execution_id>

# Full data (includes all node inputs/outputs)
./run tool/n8n_api.py execution <execution_id> --full
```

Output includes:
- Status (success/error/running/waiting)
- Workflow ID
- Started/finished timestamps
- Per-node results (what each node returned)
- Error details (which node failed, error message)

### Debugging Failed Executions

When a workflow fails:
1. Get execution list: `executions <workflow_id>`
2. Find failed execution ID (status: error)
3. Get details: `execution <exec_id> --full`
4. Look for `lastNodeExecuted` and error message
5. Check that node's input data to understand failure

### Example Debugging Flow

```bash
# 1. Check recent executions
./run tool/n8n_api.py executions abc123 10

# 2. Get details of failed one
./run tool/n8n_api.py execution exec_456 --full

# Output shows:
#   Status: error
#   Last Node: HTTP Request
#   Error: "ECONNREFUSED - Connection refused"
```

## When to Use n8n vs Python Scripts

**Use n8n when:**
- Task needs scheduling (cron triggers)
- Task is webhook-driven (receives external events)
- Flow benefits from visual debugging
- Integrating multiple SaaS tools with native n8n nodes
- Non-technical users need to understand/modify the flow

**Use Python scripts when:**
- Complex data transformations
- Heavy computation or local file processing
- Custom logic that doesn't map to n8n nodes
- One-off executions without scheduling needs

## Workflow Development Process

### Creating a New Workflow

1. **Discover** (n8n-mcp) - Find relevant nodes and templates
2. **Build** (n8n-mcp) - Generate workflow JSON with AI assistance
3. **Save** - Write to `workflows/<name>.json`
4. **Deploy** - `./run tool/n8n_api.py create workflows/<name>.json`
5. **Test** - Activate and execute, check results
6. **Version control** - Commit the JSON

### Updating an Existing Workflow

1. Export current: `./run tool/n8n_api.py export <id> workflows/<name>.json`
2. Edit the JSON or use n8n UI
3. Deploy: `./run tool/n8n_api.py update <id> workflows/<name>.json`
4. Check results: `./run tool/n8n_api.py executions <id>`

## Environment Setup

### Single Instance (Simple)

In `~/.config/cc-plugins/.env`:
```
N8N_API_URL=https://your-n8n-instance.com
N8N_API_KEY=your_api_key_here
```

### Multiple Instances (Profiles)

In `~/.config/cc-plugins/n8n.json`:
```json
{
  "profiles": {
    "production": {
      "api_url": "https://n8n.company.com",
      "api_key_env": "N8N_PROD_API_KEY",
      "description": "Production instance"
    },
    "staging": {
      "api_url": "https://staging-n8n.company.com",
      "api_key_env": "N8N_STAGING_API_KEY",
      "description": "Staging instance"
    }
  },
  "default_profile": "production"
}
```

Then add the API keys to `~/.config/cc-plugins/.env`:
```
N8N_PROD_API_KEY=your_prod_key
N8N_STAGING_API_KEY=your_staging_key
```

## Expression Syntax Quick Reference

```javascript
// Access current item's JSON data
{{ $json.fieldName }}
{{ $json.nested.field }}

// Access specific node's output
{{ $node["Node Name"].json.field }}

// Environment variables
{{ $env.MY_VAR }}

// Current execution
{{ $execution.id }}
{{ $now }}
{{ $today }}
```

## Data Table Node Reference

Data Tables provide persistent storage across workflow executions. This reference shows the exact JSON structure for each operation.

### Key Concepts

| Concept | Description |
|---------|-------------|
| `dataTableId` | Reference tables by `mode` (list/name/id) + `value` |
| `columns` (rows) | Uses resourceMapper with `mappingMode` + `value` object |
| `columns` (tables) | Uses fixedCollection with `column` array of name/type |
| Filter conditions | eq, ne, gt, gte, lt, lte, contains, isEmpty, isNotEmpty, isTrue, isFalse |
| Column types | string, number, boolean, date |
| typeVersion | Always use `1.1` for Data Table nodes |

### Row Operations

#### Insert Row

```json
{
  "parameters": {
    "resource": "row",
    "operation": "insert",
    "dataTableId": {
      "mode": "name",
      "value": "my_contacts"
    },
    "columns": {
      "mappingMode": "defineBelow",
      "value": {
        "name": "={{ $json.name }}",
        "email": "={{ $json.email }}",
        "status": "active",
        "created_at": "={{ $now.toISO() }}"
      }
    },
    "options": {
      "optimizeBulk": false
    }
  },
  "type": "n8n-nodes-base.dataTable",
  "typeVersion": 1.1
}
```

**Required**: `dataTableId`, `columns`
**Tip**: Set `optimizeBulk: true` for 5x faster batch inserts (won't return inserted data)

#### Get Rows

```json
{
  "parameters": {
    "resource": "row",
    "operation": "get",
    "dataTableId": {
      "mode": "name",
      "value": "my_contacts"
    },
    "matchType": "allConditions",
    "filters": {
      "conditions": [
        {
          "keyName": "status",
          "condition": "eq",
          "keyValue": "active"
        }
      ]
    },
    "returnAll": false,
    "limit": 50,
    "orderBy": true,
    "orderByColumn": "createdAt",
    "orderByDirection": "DESC"
  },
  "type": "n8n-nodes-base.dataTable",
  "typeVersion": 1.1
}
```

**Required**: `dataTableId`
**Optional**: `matchType`, `filters`, `returnAll`, `limit`, `orderBy*`

#### Update Rows

```json
{
  "parameters": {
    "resource": "row",
    "operation": "update",
    "dataTableId": {
      "mode": "id",
      "value": "table-uuid-here"
    },
    "matchType": "allConditions",
    "filters": {
      "conditions": [
        {
          "keyName": "email",
          "condition": "eq",
          "keyValue": "={{ $json.email }}"
        }
      ]
    },
    "columns": {
      "mappingMode": "defineBelow",
      "value": {
        "status": "updated",
        "updated_at": "={{ $now.toISO() }}"
      }
    },
    "options": {
      "dryRun": false
    }
  },
  "type": "n8n-nodes-base.dataTable",
  "typeVersion": 1.1
}
```

**Required**: `dataTableId`, `columns`
**Tip**: Use `dryRun: true` to preview changes without applying

#### Upsert Rows (Update or Insert)

```json
{
  "parameters": {
    "resource": "row",
    "operation": "upsert",
    "dataTableId": {
      "mode": "name",
      "value": "sessions"
    },
    "matchType": "allConditions",
    "filters": {
      "conditions": [
        {
          "keyName": "session_id",
          "condition": "eq",
          "keyValue": "={{ $json.sessionId }}"
        }
      ]
    },
    "columns": {
      "mappingMode": "defineBelow",
      "value": {
        "session_id": "={{ $json.sessionId }}",
        "data": "={{ JSON.stringify($json.data) }}",
        "updated_at": "={{ $now.toISO() }}"
      }
    },
    "options": {
      "dryRun": false
    }
  },
  "type": "n8n-nodes-base.dataTable",
  "typeVersion": 1.1
}
```

**Use case**: Session storage, state management, idempotent updates

#### Delete Rows

```json
{
  "parameters": {
    "resource": "row",
    "operation": "deleteRows",
    "dataTableId": {
      "mode": "name",
      "value": "my_contacts"
    },
    "matchType": "anyCondition",
    "filters": {
      "conditions": [
        {
          "keyName": "status",
          "condition": "eq",
          "keyValue": "deleted"
        }
      ]
    },
    "options": {
      "dryRun": true
    }
  },
  "type": "n8n-nodes-base.dataTable",
  "typeVersion": 1.1
}
```

**Required**: `dataTableId`
**Tip**: Always test with `dryRun: true` first

#### Row Exists (Deduplication Check)

```json
{
  "parameters": {
    "resource": "row",
    "operation": "rowExists",
    "dataTableId": {
      "mode": "name",
      "value": "processed_items"
    },
    "matchType": "allConditions",
    "filters": {
      "conditions": [
        {
          "keyName": "item_id",
          "condition": "eq",
          "keyValue": "={{ $json.id }}"
        }
      ]
    }
  },
  "type": "n8n-nodes-base.dataTable",
  "typeVersion": 1.1
}
```

**Required**: `dataTableId`, `filters` (minimum 1 condition)
**Routing**: Output 0 = row exists, Output 1 = row not found

#### Row Not Exists

Same structure as `rowExists`, but routing is inverted:
**Routing**: Output 0 = row NOT found (new item), Output 1 = row exists (duplicate)

### Table Operations

#### Create Table

```json
{
  "parameters": {
    "resource": "table",
    "operation": "create",
    "tableName": "my_contacts",
    "columns": {
      "column": [
        { "name": "name", "type": "string" },
        { "name": "email", "type": "string" },
        { "name": "age", "type": "number" },
        { "name": "is_active", "type": "boolean" },
        { "name": "created_at", "type": "date" }
      ]
    },
    "options": {
      "createIfNotExists": true
    }
  },
  "type": "n8n-nodes-base.dataTable",
  "typeVersion": 1.1
}
```

**Required**: `tableName`
**Tip**: `createIfNotExists: true` prevents errors if table already exists

#### List Tables

```json
{
  "parameters": {
    "resource": "table",
    "operation": "list",
    "returnAll": true,
    "options": {
      "filterName": "contacts",
      "sortField": "createdAt",
      "sortDirection": "desc"
    }
  },
  "type": "n8n-nodes-base.dataTable",
  "typeVersion": 1.1
}
```

#### Update Table (Rename)

```json
{
  "parameters": {
    "resource": "table",
    "operation": "update",
    "dataTableId": {
      "mode": "name",
      "value": "old_name"
    },
    "newName": "new_name"
  },
  "type": "n8n-nodes-base.dataTable",
  "typeVersion": 1.1
}
```

**Required**: `dataTableId`, `newName`

#### Delete Table

```json
{
  "parameters": {
    "resource": "table",
    "operation": "delete",
    "dataTableId": {
      "mode": "id",
      "value": "table-uuid-here"
    }
  },
  "type": "n8n-nodes-base.dataTable",
  "typeVersion": 1.1
}
```

**Warning**: Permanently deletes table and all data

### Common Filter Patterns

| Pattern | Configuration |
|---------|---------------|
| Exact match | `{ "keyName": "email", "condition": "eq", "keyValue": "user@example.com" }` |
| Not equal | `{ "keyName": "status", "condition": "ne", "keyValue": "deleted" }` |
| Contains text | `{ "keyName": "name", "condition": "contains", "keyValue": "John" }` |
| Is empty | `{ "keyName": "notes", "condition": "isEmpty" }` |
| Is not empty | `{ "keyName": "email", "condition": "isNotEmpty" }` |
| Boolean true | `{ "keyName": "is_active", "condition": "isTrue" }` |
| Boolean false | `{ "keyName": "is_active", "condition": "isFalse" }` |
| Greater than | `{ "keyName": "age", "condition": "gt", "keyValue": "18" }` |
| Less than or equal | `{ "keyName": "score", "condition": "lte", "keyValue": "100" }` |

### Data Table Templates

Ready-to-deploy workflow templates are available in `templates/`:

| Template | Purpose |
|----------|---------|
| `datatable-crud.json` | All CRUD operations demo |
| `datatable-dedup.json` | Deduplication with rowExists |
| `datatable-session.json` | Session state with upsert |

Deploy with: `./run tool/n8n_api.py create templates/datatable-crud.json`

### Validation

Before deploying workflows with Data Table nodes, validate the configuration:

```bash
./run tool/validate_datatable.py workflows/my_workflow.json
```

This catches missing required properties before deployment.

## Edge Cases & Troubleshooting

### API Limitations

- **No direct execution:** n8n API requires webhook trigger to execute
- **Webhook required:** Add a Webhook node as trigger for API execution
- **Must be active:** Workflows must be activated before webhooks work
- Use `info` command to see what triggers a workflow has

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "has no webhook trigger" | Executing workflow without webhook | Add a Webhook node |
| "is not active" | Webhook workflow not activated | Run `activate <workflow_id>` |
| "has no node to start" | Activating Manual Trigger workflow | Manual triggers are UI-only |
| 401 Unauthorized | Invalid API key | Check credentials in profile or .env |
| MCP tools not loading | mcp-wrapper not executable | Run `chmod +x mcp-wrapper` |
| Profile not found | Typo in profile name | Check `profile list` output |

### Credentials

- Workflow credentials are stored in n8n, not in exported JSON
- Exported workflows reference credentials by ID
- Re-importing to new instance requires credential reconfiguration

### Rate Limits

- n8n API has rate limits
- Batch operations if deploying many workflows
- Add delays between bulk operations

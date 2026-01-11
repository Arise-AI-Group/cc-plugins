---
name: n8n
description: This skill should be used when the user asks to "deploy n8n workflow", "list workflows", "activate workflow", "run workflow", "check workflow status". Manages n8n workflows - deploy, activate, execute, and monitor.
---

# n8n Workflow Management

## Purpose
Deploy, manage, and execute n8n workflows via the REST API. Use this for scheduled automations, webhook-driven flows, and visual pipelines that benefit from n8n's node-based interface.

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

## Execution Tool

**Location:** `tool/n8n_api.py`

### CLI Commands

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

# View execution history
./run tool/n8n_api.py executions <workflow_id>

# Export workflow to local file
./run tool/n8n_api.py export <workflow_id> workflows/exported_workflow.json

# Delete workflow (with confirmation)
./run tool/n8n_api.py delete <workflow_id>
```

### Module Usage

```python
from modules.n8n.tool.n8n_api import N8nClient

client = N8nClient()

# List workflows
workflows = client.list_workflows()

# Get specific workflow
workflow = client.get_workflow("workflow_id")

# Deploy from file
result = client.deploy_from_file("workflows/my_workflow.json")

# Execute workflow (via webhook)
result = client.execute_workflow("workflow_id", {"key": "value"})

# Get workflow test info
info = client.test_workflow("workflow_id")
```

## Workflow Development Process

### Creating a New Workflow

1. **Design in n8n UI** - Build and test the workflow visually
2. **Export to local** - `./run tool/n8n_api.py export <id> workflows/<name>.json`
3. **Version control** - Commit the JSON to the `workflows/` directory
4. **Document** - Add notes about special requirements

### Updating an Existing Workflow

1. **Edit in n8n UI** or modify the JSON directly
2. **Deploy** - `./run tool/n8n_api.py update <id> workflows/<name>.json`
3. **Test** - Use the n8n UI or call the webhook if available
4. **Check results** - `./run tool/n8n_api.py executions <id>`

## Environment Variables

Required in `.env`:
```
N8N_API_URL=https://your-n8n-instance.com
N8N_API_KEY=your_api_key_here
```

To get your API key:
1. Open your n8n instance
2. Go to Settings > API
3. Create a new API key

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

## Edge Cases & Learnings

### API Limitations

- **No direct execution:** The n8n public API does not support direct workflow execution. The `execute` command works by calling the workflow's webhook trigger.
- **Webhook required:** To execute a workflow via API, it must have a Webhook node as its trigger.
- **Must be active:** Workflows must be activated before their webhooks are accessible.

### Activation Rules

- **Manual Trigger workflows** cannot be "activated" - they're designed for manual runs in the UI only
- **Webhook/Schedule triggers** must be activated to run automatically
- Use `info` command to see what triggers a workflow has

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "has no webhook trigger" | Trying to execute workflow without webhook | Add a Webhook node to the workflow |
| "is not active" | Webhook workflow not activated | Run `activate <workflow_id>` |
| "has no node to start" | Trying to activate Manual Trigger workflow | Manual Trigger workflows can only be run from UI |
| 401 Unauthorized | Invalid API key | Check `N8N_API_KEY` in `.env` |

### Credentials

- Workflow credentials are stored in n8n, not in the JSON
- Exported workflows reference credentials by ID
- When importing to a new instance, you'll need to reconfigure credentials

### Rate Limits

- n8n API has rate limits
- Batch operations if deploying many workflows
- Add delays between bulk operations


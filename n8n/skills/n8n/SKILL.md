---
name: n8n
description: This skill should be used when the user asks to "deploy n8n workflow", "list workflows", "activate workflow", "run workflow", "check workflow status", "find n8n node", "search workflow templates", "build new workflow", "what nodes does n8n have", "how do I write n8n expressions", "validate my workflow", "configure this n8n node", "write code node", "n8n patterns". Manages n8n workflows - discover nodes via MCP, deploy/execute via CLI, with expert knowledge on expressions, patterns, validation, and code nodes.
---

# n8n Workflow Management

## Session Start: Instance Selection

**FIRST ACTION** when this skill loads with multiple profiles configured:

1. Run `./run tool/n8n_api.py profile list`
2. If multiple profiles exist, ASK the user which instance to use:
   > "I see you have multiple n8n instances configured. Which instance should I use for this session?"
3. If user selects non-default, run `profile switch <name>` and inform:
   > "Switched to [name]. Note: MCP tools use the instance from when Claude Code started. Restart or /clear to sync."
4. If only one profile, proceed silently with default.

## Context Efficiency

Full workflow MCP tools are **disabled** to prevent context bloat. Use CLI file-based operations instead.

### Workflow Operations (CLI Only)

| Operation | CLI Command |
|-----------|-------------|
| Get workflow | `export <id> <file>` → then `Read` file |
| Create workflow | `Write` file → then `create <file>` |
| Update workflow | `export` → `Edit` → `update <id> <file>` |
| Get template | `template-get <id> <file>` → then `Read` file |

### MCP Tools (Available)

| Tool | Use Case | Context Cost |
|------|----------|--------------|
| `search_nodes` | Node discovery | LOW |
| `get_node` detail=standard | Quick lookup | LOW |
| `n8n_list_workflows` | List workflow metadata | LOW |
| `n8n_update_partial_workflow` | Surgical changes | LOW |
| `n8n_validate_workflow` | Validate deployed workflow | LOW |
| `n8n_deploy_template` | Deploy from n8n.io | MEDIUM |
| `n8n_executions` | Execution history | LOW-MEDIUM |

### MCP Tools (Disabled)

These tools are disabled to enforce CLI usage:
- `n8n_create_workflow` → use CLI `create`
- `n8n_update_full_workflow` → use CLI `update`
- `n8n_get_workflow` → use CLI `export`

## Two Integrated Tools

### n8n-mcp (MCP Server) - Discovery & Building

Use for questions about n8n capabilities:
- "What nodes work with Slack?"
- "Find a template for automation"
- "What parameters does HTTP Request accept?"

Capabilities: 1,084+ nodes documented, 2,709 workflow templates searchable.

### n8n CLI (Python) - Operations & Management

Use for managing deployed workflows:
- List/get/export workflows
- Deploy workflow JSON files
- Activate/deactivate workflows
- Execute and monitor

**Combined Workflow:**
```
1. CHECK INSTANCE: ./run tool/n8n_api.py profile list
2. DISCOVER (MCP): search_nodes, get_node
3. BUILD (MCP): Help design workflow
4. SAVE: Write JSON to workflows/
5. DEPLOY (CLI): ./run tool/n8n_api.py create workflows/file.json
6. ACTIVATE (CLI): ./run tool/n8n_api.py activate <id>
7. TEST (CLI): ./run tool/n8n_api.py execute <id>
```

## Multi-Instance Support

### Profile Commands

```bash
./run tool/n8n_api.py profile list                           # List all instances
./run tool/n8n_api.py profile add <name> --url <url> --api-key-env <env_var>
./run tool/n8n_api.py profile default <name>                 # Set default
./run tool/n8n_api.py profile switch <name>                  # Switch instance
./run tool/n8n_api.py --profile <name> <command>             # Per-command override
```

### CLI vs MCP Instance Handling

| Tool | When Profile Read | How to Switch |
|------|-------------------|---------------|
| CLI commands | Per-command | `--profile` flag or `profile switch` |
| MCP tools | At Claude Code startup | Restart Claude Code |

## CLI Quick Reference

### Workflow Operations

```bash
./run tool/n8n_api.py list                                   # List all workflows
./run tool/n8n_api.py info <id>                              # Lightweight info
./run tool/n8n_api.py summary <id>                           # Node counts
./run tool/n8n_api.py create workflows/file.json             # Deploy new
./run tool/n8n_api.py update <id> file.json                  # Update existing
./run tool/n8n_api.py activate <id>                          # Activate
./run tool/n8n_api.py deactivate <id>                        # Deactivate
./run tool/n8n_api.py export <id> output.json                # Export to file
./run tool/n8n_api.py diff <id> local.json                   # Compare versions
./run tool/n8n_api.py validate file.json                     # Validate JSON
./run tool/n8n_api.py delete <id>                            # Delete (with confirm)
```

### Execution Monitoring

```bash
./run tool/n8n_api.py executions <workflow_id> [limit]       # Execution history
./run tool/n8n_api.py execution <exec_id>                    # Summary view
./run tool/n8n_api.py execution <exec_id> --full             # Full details
./run tool/n8n_api.py execution-export <exec_id> debug.json  # Export to file
```

### Template Operations (from n8n.io)

```bash
./run tool/n8n_api.py template-get <id> <output_file>        # Download template to file
./run tool/n8n_api.py template-info <id>                     # View template metadata
```

## Expert Knowledge References

For detailed guidance on specific topics, see these reference documents:

| Reference | Use When |
|-----------|----------|
| [expression-syntax.md](references/expression-syntax.md) | Writing expressions, accessing webhook data, using $json/$node |
| [mcp-tools-expert.md](references/mcp-tools-expert.md) | Choosing MCP tools, nodeType formats, validation profiles |
| [workflow-patterns.md](references/workflow-patterns.md) | Designing new workflows, choosing architecture patterns |
| [validation-expert.md](references/validation-expert.md) | Fixing validation errors, understanding auto-sanitization |
| [node-configuration.md](references/node-configuration.md) | Configuring specific nodes, property dependencies, Data Table nodes |
| [code-javascript.md](references/code-javascript.md) | Writing JavaScript in Code nodes |
| [code-python.md](references/code-python.md) | Writing Python in Code nodes (limited - prefer JavaScript) |

## Environment Setup

### Single Instance

In `~/.config/cc-plugins/.env`:
```
N8N_API_URL=https://your-n8n-instance.com
N8N_API_KEY=your_api_key_here
```

### Multiple Instances

In `~/.config/cc-plugins/n8n.json`:
```json
{
  "profiles": {
    "production": {
      "api_url": "https://n8n.company.com",
      "api_key_env": "N8N_PROD_API_KEY"
    },
    "staging": {
      "api_url": "https://staging-n8n.company.com",
      "api_key_env": "N8N_STAGING_API_KEY"
    }
  },
  "default_profile": "production"
}
```

Then add API keys to `~/.config/cc-plugins/.env`:
```
N8N_PROD_API_KEY=your_prod_key
N8N_STAGING_API_KEY=your_staging_key
```

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "has no webhook trigger" | Executing workflow without webhook | Add Webhook node |
| "is not active" | Webhook workflow not activated | Run `activate <id>` |
| "has no node to start" | Activating Manual Trigger workflow | Manual triggers are UI-only |
| 401 Unauthorized | Invalid API key | Check credentials in profile |
| MCP tools not loading | mcp-wrapper not executable | Run `chmod +x mcp-wrapper` |
| Profile not found | Typo in profile name | Check `profile list` output |

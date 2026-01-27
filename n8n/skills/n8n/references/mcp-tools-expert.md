# n8n MCP Tools Expert Reference

## Tool Categories

### Node Discovery (Low Context)

| Tool | Purpose | Response Time |
|------|---------|---------------|
| `search_nodes` | Find nodes by keyword | <20ms |
| `get_node` detail=minimal | Quick property check | <50ms |
| `get_node` detail=standard | Full properties (default) | <100ms |
| `get_node` mode=docs | Readable documentation | <100ms |

### Workflow Management (Variable Context)

| Tool | Purpose | Context Cost |
|------|---------|--------------|
| `n8n_list_workflows` | List all workflows | LOW |
| `n8n_get_workflow` mode=minimal | Quick status check | LOW |
| `n8n_get_workflow` mode=structure | Nodes and connections | MEDIUM |
| `n8n_get_workflow` mode=full | Complete workflow | HIGH |
| `n8n_update_partial_workflow` | Surgical updates | LOW |
| `n8n_create_workflow` | Create new workflow | HIGH |
| `n8n_update_full_workflow` | Replace entire workflow | HIGH |

### Templates

| Tool | Purpose |
|------|---------|
| `search_templates` | Find workflow templates |
| `get_template` | Get template details |
| `n8n_deploy_template` | Deploy template to instance |

### Validation

| Tool | Purpose |
|------|---------|
| `validate_node` | Check single node config |
| `validate_workflow` | Check entire workflow |
| `n8n_validate_workflow` | Validate deployed workflow |
| `n8n_autofix_workflow` | Auto-fix common issues |

## Critical: nodeType Formats

Different tools require different formats:

### Format 1: Search/Validate Tools

Use **short format** without `n8n-` prefix:

```
nodes-base.slack
nodes-base.httpRequest
nodes-langchain.agent
```

Tools using this format: `search_nodes`, `get_node`, `validate_node`

### Format 2: Workflow Creation Tools

Use **full format** with `n8n-` prefix:

```
n8n-nodes-base.slack
n8n-nodes-base.httpRequest
n8n-nodes-langchain.agent
```

Tools using this format: `n8n_create_workflow`, `n8n_update_full_workflow`

### Quick Conversion

```
short -> full: Add "n8n-" prefix
full -> short: Remove "n8n-" prefix
```

## Validation Profiles

Always specify a validation profile explicitly:

| Profile | Use When | Behavior |
|---------|----------|----------|
| `minimal` | Quick editing | Required fields only |
| `runtime` | Pre-deployment (recommended) | Balanced checking |
| `ai-friendly` | AI-generated configs | Reduces false positives |
| `strict` | Production-critical | Maximum validation |

**Default recommendation**: Use `runtime` for most validation tasks.

## Detail Levels for get_node

| Level | Tokens | Use When |
|-------|--------|----------|
| `minimal` | ~200 | Just checking if node exists |
| `standard` | 1-2K | Normal configuration (95% of cases) |
| `full` | 3-8K | Complex debugging, AI agent nodes |

**Always start with `standard`** - only use `full` when needed.

## Auto-Sanitization Behavior

When you save/update any workflow, n8n-mcp automatically fixes:

**Binary Operators** (two arguments):
- Removes inappropriate `singleValue` property
- Affected: `equals`, `contains`, `greaterThan`, `lessThan`, etc.

**Unary Operators** (one argument):
- Adds required `singleValue: true`
- Affected: `isEmpty`, `isNotEmpty`, `true`, `false`

**What auto-sanitization CANNOT fix:**
- Broken node connections
- Missing required fields
- Invalid node references
- Branch count mismatches

## Smart Parameters

Modern workflow tools support semantic parameters:

```javascript
// Instead of calculating sourceIndex manually:
{
  "branch": "true",      // Connect to "true" branch of IF node
  "case": 0,             // Connect to case 0 of Switch node
  "intent": "greeting"   // Connect to specific AI tool
}
```

## Common Mistakes and Fixes

| Mistake | Fix |
|---------|-----|
| Using `n8n-nodes-base.slack` in search_nodes | Use `nodes-base.slack` |
| Using `nodes-base.slack` in create_workflow | Use `n8n-nodes-base.slack` |
| get_node with detail=full for simple lookup | Use detail=standard |
| Passing full workflow JSON to create_workflow | Write to file, use CLI instead |
| No validation profile specified | Always specify `profile: "runtime"` |

## Tool Availability by Setup

| Setup | Available Tools |
|-------|-----------------|
| MCP only (no API key) | search_nodes, get_node, validate_node, search_templates, get_template |
| MCP + API key | All above + n8n_* workflow management tools |

## Recommended Workflows

### Building a New Workflow

1. `search_nodes` - Find relevant nodes
2. `get_node` detail=standard - Get configuration details
3. `search_templates` - Find similar workflows
4. Write workflow JSON to file
5. CLI: `./run tool/n8n_api.py create file.json`

### Debugging Validation Errors

1. `validate_workflow` with profile=runtime
2. Read error messages carefully
3. Use `get_node` mode=search_properties to find correct field names
4. Fix and re-validate
5. Trust auto-sanitization for operator issues

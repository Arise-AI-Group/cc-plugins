# n8n

AI-assisted n8n workflow development and management

## Features

- **Discovery**: Search 1,084+ nodes with documentation via n8n-mcp
- **Templates**: Browse 2,709 workflow templates for inspiration
- **Building**: AI-assisted workflow JSON generation
- **Deployment**: Deploy, activate, and manage workflows via REST API
- **Execution**: Trigger workflows and monitor execution history
- **Multi-instance**: Switch between production, staging, and client instances

## Installation

```bash
/plugin install n8n@cc-plugins
```

## Quick Start

### Build a New Workflow

```
"Help me build an n8n workflow that monitors a Google Sheet and posts updates to Slack"
```

### Deploy and Run

```bash
./run tool/n8n_api.py create workflows/my_workflow.json
./run tool/n8n_api.py activate <workflow_id>
./run tool/n8n_api.py executions <workflow_id>
```

### Multi-Instance Usage

```bash
# List configured instances
./run tool/n8n_api.py profile list

# Add a new instance
./run tool/n8n_api.py profile add staging \
  --url https://staging-n8n.example.com \
  --api-key-env N8N_STAGING_API_KEY \
  --description "Staging instance"

# Set default instance
./run tool/n8n_api.py profile default staging

# Use specific instance
./run tool/n8n_api.py --profile production list
```

## Environment Variables

### Single Instance

In `~/.config/cc-plugins/.env`:

```
N8N_API_URL=https://your-n8n-instance.com
N8N_API_KEY=your_api_key_here
```

### Multiple Instances

Profiles are stored in `~/.config/cc-plugins/n8n.json`:

```json
{
  "profiles": {
    "production": {
      "api_url": "https://n8n.company.com",
      "api_key_env": "N8N_PROD_API_KEY",
      "description": "Production instance"
    }
  },
  "default_profile": "production"
}
```

## Architecture

This plugin combines two tools:

| Tool | Method | Purpose |
|------|--------|---------|
| n8n-mcp | MCP Server | Node discovery, templates, building |
| n8n_api.py | Python CLI | Deploy, execute, monitor |

## Skills

Auto-triggered when you ask about:
- Building n8n workflows
- Finding n8n nodes
- Deploying workflows
- Executing workflows
- Checking execution status

## CLI Commands

```bash
./run tool/n8n_api.py list                              # List workflows
./run tool/n8n_api.py get <id>                          # Get workflow JSON
./run tool/n8n_api.py info <id>                         # Get workflow info
./run tool/n8n_api.py create <file>                     # Deploy new workflow
./run tool/n8n_api.py update <id> <file>                # Update workflow
./run tool/n8n_api.py activate <id>                     # Activate workflow
./run tool/n8n_api.py deactivate <id>                   # Deactivate workflow
./run tool/n8n_api.py execute <id> [json]               # Execute via webhook
./run tool/n8n_api.py executions <id> [limit]           # View execution history
./run tool/n8n_api.py execution <exec_id> [--full]      # Get execution details
./run tool/n8n_api.py export <id> <file>                # Export to file
./run tool/n8n_api.py delete <id>                       # Delete workflow
./run tool/n8n_api.py profile list                      # List profiles
./run tool/n8n_api.py profile add <name> ...            # Add profile
./run tool/n8n_api.py profile default <name>            # Set default
./run tool/n8n_api.py profile remove <name>             # Remove profile
```

## License

MIT

# CC Plugins

Portable Claude Code plugins for AI-agent-powered automation.

Each plugin is self-contained and follows the [official Claude Code plugin standard](https://code.claude.com/docs/en/plugins).

## Quick Start (No Cloning Required!)

### 1. Add the Plugin Marketplace

```bash
/plugin marketplace add arisegroup/cc-plugins
```

This registers the GitHub repository as a plugin marketplace in Claude Code.

### 2. Browse & Install Plugins

**Interactive (recommended):** Run `/plugin` to open the plugin manager, then:
- Go to the **Discover** tab to browse all available plugins
- Press **Enter** on a plugin to install it
- Choose your installation scope (user, project, or local)

**Command line:** If you know what you want:
```bash
/plugin install core@cc-plugins       # Setup skill (recommended first)
/plugin install slack@cc-plugins      # Slack channel management
/plugin install notion@cc-plugins     # Notion page/database operations
```

### 3. Configure Credentials

Say **"set up cc-plugins"** or trigger the setup skill. This creates `~/.config/cc-plugins/.env` with your API keys.

Or manually create the file:

```bash
mkdir -p ~/.config/cc-plugins
nano ~/.config/cc-plugins/.env
```

### 4. Start Using

Plugins auto-load in every Claude Code session. Just describe what you want:

```
"Create a Slack channel for the Acme project"
"Search Notion for meeting notes"
"Deploy a demo app from owner/repo"
```

## Available Plugins

| Plugin | Description |
|--------|-------------|
| [core](./core/) | Setup skill for credential configuration |
| [slack](./slack/) | Slack channel and message management |
| [notion](./notion/) | Notion page and database operations |
| [n8n](./n8n/) | n8n workflow management |
| [infrastructure](./infrastructure/) | Cloudflare DNS/tunnels, Dokploy containers |
| [leads](./leads/) | Lead scraping and verification |
| [diagrams](./diagrams/) | Diagram generation (Draw.io, Mermaid) |
| [sop](./sop/) | Audio transcription and SOP extraction |
| [md-export](./md-export/) | Markdown to Google Docs/Word export |
| [proposal](./proposal/) | Sales proposal generation |
| [demo-deploy](./demo-deploy/) | Demo application deployment |
| [client-onboarding](./client-onboarding/) | Client workspace setup |
| [ssh](./ssh/) | Remote SSH/SFTP operations |

## Environment Variables

All plugins read credentials from `~/.config/cc-plugins/.env`. This file is NOT part of the repository - you create it locally with your own API keys.

| Plugin | Required Variables |
|--------|-------------------|
| slack | `SLACK_BOT_TOKEN`, `SLACK_USER_TOKEN` |
| notion | `NOTION_API_KEY` |
| n8n | `N8N_API_URL`, `N8N_API_KEY` |
| infrastructure | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `DOKPLOY_URL`, `DOKPLOY_API_KEY` |
| diagrams | `OPENAI_API_KEY` |
| sop | `OPENAI_API_KEY` |
| leads | `APIFY_TOKEN` |
| md-export | `GOOGLE_FOLDER_ID` |
| proposal | `GOOGLE_SLIDES_TEMPLATE_ID` |
| ssh | `SSH_KEY_PATH`, `SSH_PASSWORD` |
| demo-deploy | `DOKPLOY_URL`, `DOKPLOY_API_KEY`, `BASE_DOMAIN` |
| client-onboarding | `SLACK_BOT_TOKEN`, `SLACK_USER_TOKEN` |

See `.env.example` for a complete template.

## Using Plugins

### Skills (Natural Language)

Just describe what you want:

- "Create a Slack channel for the Acme project"
- "Summarize the Slack messages from #project-acme"
- "Create a diagram showing the user authentication flow"
- "Generate a proposal for this client"

### Commands (Explicit)

Use slash commands for direct control:

- `/slack:skills` - Slack operations
- `/notion:skills` - Notion operations
- `/diagrams:skills` - Diagram generation

## Plugin Management

```bash
# List installed plugins
/plugins

# Enable/disable a plugin
/plugin enable slack@cc-plugins
/plugin disable slack@cc-plugins

# Uninstall
/plugin uninstall slack@cc-plugins
```

## For Developers

Development requires cloning the repository. End users don't need to clone - they install plugins directly from the marketplace.

### Cloning the Repository

```bash
git clone https://github.com/arisegroup/cc-plugins.git
cd cc-plugins
python -m venv .venv && source .venv/bin/activate
```

### Repository Structure

```
cc-plugins/
├── .claude-plugin/
│   └── marketplace.json         # Marketplace manifest (lists all plugins)
├── tools/                       # Developer utilities (require cloning)
│   ├── plugin-scaffold.py       # Create new plugins from template
│   └── generate-tests.py        # Generate test files
├── core/                        # Setup skill plugin
├── slack/                       # Slack plugin
├── notion/                      # Notion plugin
├── ...                          # Other plugins
├── .env.example                 # Template for credentials
└── README.md
```

### Plugin Structure

Each plugin is self-contained:

```
{plugin}/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest (required)
├── skills/
│   └── *.md                     # Auto-triggered procedures
├── tool/
│   ├── config.py                # Credential loader (reads ~/.config/cc-plugins/.env)
│   └── {module}_api.py          # Python CLI tool
├── requirements.txt             # Python dependencies
├── run                          # Venv wrapper script
└── README.md                    # Plugin documentation
```

### Creating New Plugins

Use the scaffold tool to create a new plugin with all boilerplate:

```bash
python tools/plugin-scaffold.py myservice \
  --description "My service integration" \
  --env-vars "API_KEY,API_SECRET"
```

This creates:
- Plugin manifest (`.claude-plugin/plugin.json`)
- Skill template (`skills/myservice.md`)
- Tool with credential loading (`tool/myservice_api.py`, `tool/config.py`)
- Requirements file with `python-dotenv`
- README template

After creating, add your plugin to `marketplace.json` to make it installable.

### Adding to Marketplace

Edit `.claude-plugin/marketplace.json` and add your plugin:

```json
{
  "plugins": [
    ...existing plugins...,
    {
      "name": "myservice",
      "source": "./myservice",
      "description": "My service integration"
    }
  ]
}
```

### Testing Locally

While developing, you can test your plugin locally before pushing:

```bash
# Install from local directory
/plugin install /path/to/cc-plugins/myservice

# Or enable the whole marketplace locally
/plugin marketplace add /path/to/cc-plugins
```

## Requirements

- Claude Code CLI or VS Code extension
- Python 3.9+ (for plugins with Python tools)

## License

MIT

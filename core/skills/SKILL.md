---
name: setup
description: This skill should be used when the user asks to "set up cc-plugins", "configure credentials", "add API keys", "initialize plugins". Provides interactive onboarding that detects installed plugins and configures required credentials.
---

# CC-Plugins Setup

## Purpose
Help team members configure API credentials for their installed CC-Plugins.
This skill detects which plugins are installed and prompts only for the credentials they need.

## When to Use This Skill

**Trigger phrases:**
- "Set up cc-plugins"
- "Configure my API keys"
- "I'm new, help me get started"
- "Setup the plugins"
- "Import my .env file"
- "Use my existing .env at /path/to/.env"

## Quick Setup: Import Existing .env File

If the user already has a .env file with their credentials, they can import it directly:

**Trigger phrases:**
- "Set up cc-plugins with /path/to/.env"
- "Import /path/to/.env for cc-plugins"
- "Use my .env at ~/projects/.env"

### Import Process

1. **Read the source file** - Verify it exists and is readable
2. **Create config directory**:
   ```bash
   mkdir -p ~/.config/cc-plugins
   ```
3. **Copy the file**:
   ```bash
   cp /path/to/source/.env ~/.config/cc-plugins/.env
   ```
4. **Detect installed plugins** - Check what's installed
5. **Validate credentials** - Check if required keys are present for each installed plugin
6. **Report status** - Tell user which plugins are configured and which are missing credentials

### Validation Rules

For each installed plugin, check if the required variables exist in the imported file:
- **slack**: `SLACK_BOT_TOKEN`
- **notion**: `NOTION_API_KEY`
- **n8n**: `N8N_API_URL`, `N8N_API_KEY`
- **infrastructure**: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`
- **diagrams**: `OPENAI_API_KEY`
- **sop**: `OPENAI_API_KEY`
- **leads**: `APIFY_TOKEN`
- **demo-deploy**: `DOKPLOY_URL`, `DOKPLOY_API_KEY`
- **client-onboarding**: `SLACK_BOT_TOKEN`

If any required variables are missing, list them and offer to add them interactively.

---

## Interactive Setup (From Scratch)

### Step 1: Create Config Directory
```bash
mkdir -p ~/.config/cc-plugins
```

### Step 2: Detect Installed Plugins

Check which cc-plugins are installed by looking at:
```bash
ls ~/.claude/plugins/cache/cc-plugins/ 2>/dev/null || echo "No plugins installed yet"
```

### Step 3: Collect Credentials Based on Installed Plugins

For each installed plugin, prompt for its required credentials:

#### slack
| Variable | Required | How to Get |
|----------|----------|------------|
| `SLACK_BOT_TOKEN` | Yes | https://api.slack.com/apps → Your App → OAuth & Permissions → Bot User OAuth Token (starts with `xoxb-`) |
| `SLACK_USER_TOKEN` | Optional | Same page → User OAuth Token (starts with `xoxp-`). Needed for huddles/canvases. |

#### notion
| Variable | Required | How to Get |
|----------|----------|------------|
| `NOTION_API_KEY` | Yes | https://www.notion.so/my-integrations → Your Integration → Internal Integration Secret (starts with `secret_`) |

#### n8n
| Variable | Required | How to Get |
|----------|----------|------------|
| `N8N_API_URL` | Yes | Your n8n instance URL (e.g., `https://n8n.example.com`) |
| `N8N_API_KEY` | Yes | n8n Settings → API → Create API Key |

#### infrastructure
| Variable | Required | How to Get |
|----------|----------|------------|
| `CLOUDFLARE_API_TOKEN` | Yes | https://dash.cloudflare.com/profile/api-tokens → Create Token |
| `CLOUDFLARE_ACCOUNT_ID` | Yes | Cloudflare dashboard → Account ID (in sidebar) |
| `DOKPLOY_URL` | Optional | Your Dokploy instance URL |
| `DOKPLOY_API_KEY` | Optional | Dokploy Settings → API Keys |

#### diagrams
| Variable | Required | How to Get |
|----------|----------|------------|
| `OPENAI_API_KEY` | Yes | https://platform.openai.com/api-keys → Create new secret key |

#### sop
| Variable | Required | How to Get |
|----------|----------|------------|
| `OPENAI_API_KEY` | Yes | https://platform.openai.com/api-keys (same as diagrams) |

#### leads
| Variable | Required | How to Get |
|----------|----------|------------|
| `APIFY_TOKEN` | Yes | https://console.apify.com/account/integrations → API token |

#### md-export
| Variable | Required | How to Get |
|----------|----------|------------|
| `GOOGLE_FOLDER_ID` | Optional | Google Drive folder ID from URL (the long string after `/folders/`) |

Google OAuth setup: Run the tool once, it will open a browser for OAuth consent.

#### proposal
| Variable | Required | How to Get |
|----------|----------|------------|
| `GOOGLE_SLIDES_TEMPLATE_ID` | Yes | Google Slides presentation ID from URL |

Google OAuth setup: Same as md-export.

#### demo-deploy
| Variable | Required | How to Get |
|----------|----------|------------|
| `DOKPLOY_URL` | Yes | Your Dokploy instance URL |
| `DOKPLOY_API_KEY` | Yes | Dokploy Settings → API Keys |
| `BASE_DOMAIN` | Optional | Base domain for demo apps (default: `arisegroup-tools.com`) |

#### client-onboarding
| Variable | Required | How to Get |
|----------|----------|------------|
| `SLACK_BOT_TOKEN` | Yes | Same as slack plugin |
| `SLACK_USER_TOKEN` | Optional | Same as slack plugin |

#### ssh
| Variable | Required | How to Get |
|----------|----------|------------|
| `SSH_KEY_PATH` | Optional | Path to SSH private key (e.g., `~/.ssh/id_rsa`) |
| `SSH_PASSWORD` | Optional | SSH password (if not using key auth) |

### Step 4: Write Credentials File

Create or update `~/.config/cc-plugins/.env` with the collected credentials.

Example file structure:
```bash
# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_USER_TOKEN=xoxp-...

# Notion
NOTION_API_KEY=secret_...

# OpenAI (for diagrams, sop)
OPENAI_API_KEY=sk-...

# Add other credentials as needed...
```

### Step 5: Verify Setup

Test each plugin by asking Claude to perform a simple operation:
- **slack**: "List my Slack channels"
- **notion**: "Search Notion for test"
- **n8n**: "List n8n workflows"
- **infrastructure**: "List Cloudflare zones"

## Interactive Flow

When a user says "set up cc-plugins", follow this flow:

1. **Check for existing .env** - Ask if they have an existing .env file to import
   - If yes: Follow the Import Process above
   - If no: Continue with interactive setup
2. **Check installed plugins** - Run the detection command
3. **Greet and explain** - Tell them what plugins you found
4. **For each plugin**:
   - Explain what credentials are needed
   - Provide the link to get them
   - Ask the user to paste the value
5. **Write the .env file** - Create/update with all collected values
6. **Verify** - Offer to test each plugin

## Troubleshooting

### "Token not configured"
The `.env` file is missing or the variable isn't set. Check:
```bash
cat ~/.config/cc-plugins/.env
```

### "Invalid token" errors
- Verify no extra spaces or newlines in the token
- Check the token hasn't been revoked
- Ensure proper scopes/permissions

### Notion "Object not found"
The integration needs to be connected to pages:
1. Open the Notion page
2. Click "..." menu → "Add connections"
3. Select your integration

### Google OAuth issues
For md-export and proposal, you need OAuth credentials:
1. Create a project at https://console.cloud.google.com
2. Enable Drive and Slides APIs
3. Create OAuth credentials (Desktop app)
4. Download as `credentials.json` in the plugin directory
5. Run the tool once to complete OAuth flow

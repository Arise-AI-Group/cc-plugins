# CC-Plugins Contributor Guide

This guide is for contributors developing plugins in Claude Code for this repository.

## Required Setup

Before developing plugins, install the Anthropic plugin-dev plugin:

```
/plugin install plugin-dev@claude-code-marketplace
```

This provides specialized skills for plugin development (hooks, MCP, structure, settings, commands, agents, skills) and enables the `/plugin-dev:create-plugin` guided workflow.

## Core Principle: Reference Existing Plugins

**Always explore existing plugins before building new functionality.** Use established patterns from working plugins as templates.

Recommended reference plugins:
- `slack/` - Full-featured plugin with comprehensive SKILL.md, Python CLI wrapper
- `notion/` - Python API wrapper with rich CLI interface and block operations
- `infrastructure/` - Multiple service integrations (Cloudflare, Dokploy)

When creating new plugins:
1. Read the SKILL.md of a similar plugin
2. Copy the `config.py` and `run` script (these are standardized)
3. Follow the same CLI argument patterns (`--output-format`, `--help`)
4. Match the SKILL.md documentation structure

## Credential Management

**All credentials go in `~/.config/cc-plugins/.env`** - never in the repository.

Guidelines:
- Use the standard `config.py` from any existing plugin (they're identical)
- Namespace environment variables: `SERVICENAME_API_KEY`, `SERVICENAME_SECRET`
- Update `.env.example` when adding new required variables
- Run the `core` plugin setup skill for initial configuration: "set up cc-plugins"

## Plugin Structure

Follow this established directory layout:

```
{plugin}/
├── .claude-plugin/plugin.json   # Manifest (name, description, version, author)
├── skills/                      # Auto-triggered procedures (required)
│   └── SKILL.md                 # Simple skill (or subdirectory for advanced)
├── tool/
│   ├── config.py                # Credential loader (copy from existing plugin)
│   └── {service}_api.py         # Python CLI implementation
├── run                          # Venv wrapper (copy from existing plugin)
├── setup.sh                     # Setup script
├── requirements.txt             # Dependencies (always include python-dotenv)
└── README.md                    # Plugin documentation
```

Use the scaffold tool to create new plugins with all boilerplate:

```bash
python tools/plugin-scaffold.py myservice \
  --description "My service integration" \
  --env-vars "API_KEY,API_SECRET"
```

## Skill Structure

### Simple Skills (recommended for most plugins)

For skills under 1,500 words, use the flat structure:

```
{plugin}/skills/SKILL.md
```

### Advanced Skills (for comprehensive documentation)

For skills over 1,500 words, use the subdirectory structure with progressive disclosure:

```
{plugin}/skills/{skill-name}/
├── SKILL.md                 # Core content (1,500-2,000 words max)
├── references/              # Detailed documentation
│   ├── cli-reference.md     # Exhaustive CLI commands
│   └── edge-cases.md        # Known issues, limitations
└── examples/                # Working code examples
    └── workflows.md         # Common workflow patterns
```

**When to use advanced structure:**
- SKILL.md exceeds 1,500 words
- Multiple distinct subsystems (e.g., infrastructure has Cloudflare + Dokploy + Supabase)
- Extensive CLI reference that would overwhelm the main skill file

**Progressive disclosure pattern:**
- SKILL.md contains triggers, purpose, quick reference, and pointers to detailed docs
- `references/` contains exhaustive documentation Claude loads when needed
- `examples/` contains working code samples

## SKILL.md Documentation Standards

### YAML Frontmatter

Use third-person descriptions with quoted trigger phrases:

```yaml
---
name: {plugin-name}
description: This skill should be used when the user asks to "trigger phrase 1", "trigger phrase 2", "trigger phrase 3". Brief capability summary.
---
```

**Example:**
```yaml
---
name: notion
description: This skill should be used when the user asks to "create a Notion page", "query the database", "search Notion for", "add content to page". Provides Notion API integration for pages, databases, blocks, and search.
---
```

### Content Requirements

Every SKILL.md must include:

1. **YAML frontmatter** with `name` and `description` (using format above)
2. **Trigger phrases** section with bullet list of activation phrases
3. **Execution method** - which Python tool to use
4. **Core operations** - condensed command reference with common use cases
5. **Environment variables** required
6. **Pointers to references** (for advanced skills with subdirectories)

### Writing Style

- Use **imperative/infinitive form** (not second person)
  - Good: "To create a page, run..."
  - Avoid: "You can create a page by running..."
- Keep SKILL.md under **2,000 words** (target 1,500-1,800 for complex skills)
- Move detailed CLI flags, edge cases, and examples to `references/` and `examples/`

### Reference Plugins

Study these as templates:
- `slack/skills/SKILL.md` - Well-structured simple skill
- `notion/skills/notion/` - Advanced skill with progressive disclosure (after refactor)
- `infrastructure/skills/infrastructure/` - Multi-service advanced skill (after refactor)

## Testing Requirements

Before committing:

1. **Test locally**: `/plugin install /path/to/cc-plugins/{plugin}`
2. **Run test script** if available: `./test.sh`
3. **Verify CLI help**: `./run tool/{service}_api.py --help`
4. **Generate tests**: `python tools/generate-tests.py {plugin}`

## Marketplace Registration

After creating a plugin:

1. Add entry to `.claude-plugin/marketplace.json`:
   ```json
   {
     "name": "myservice",
     "source": "./myservice",
     "description": "My service integration"
   }
   ```

2. Bump version in your plugin's `.claude-plugin/plugin.json`

## Using plugin-dev Skills

The plugin-dev plugin provides expert guidance. Ask Claude:

- "What's the best structure for this plugin?" (triggers plugin-structure skill)
- "Create a hook to validate X" (triggers hook-development skill)
- "How do I add MCP integration?" (triggers mcp-integration skill)
- Use `/plugin-dev:create-plugin` for end-to-end guided creation

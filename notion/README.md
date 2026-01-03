# agentic-notion

Notion page, database, and block management - create pages, query databases, manage content blocks, and search workspace

## Installation

```bash
# Set up the plugin
./setup.sh

# Edit .env with your credentials
nano .env

# Run Claude Code with this plugin
claude --plugin-dir .
```

## Commands

- `/agentic-notion:*` - See available commands with `/help`

## Environment Variables

- `NOTION_API_KEY`

## Usage

### Via Slash Commands

```
/agentic-notion:<action> [args]
```

### Via CLI

```bash
./run tool/notion_api.py <action> [args]
./run tool/notion_api.py --help
```

## Skills

This plugin includes auto-triggered skills that activate when you describe related tasks.
Claude will automatically use the appropriate procedures when you ask about:
- Notion page, database, and block management - create pages, query databases, manage content blocks, and search workspace

## License

MIT

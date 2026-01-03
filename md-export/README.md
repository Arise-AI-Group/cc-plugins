# agentic-md-export

Export markdown to Google Docs and Word documents with Mermaid diagram rendering

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

- `/agentic-md-export:*` - See available commands with `/help`

## Environment Variables

- `GOOGLE_FOLDER_ID`

## Usage

### Via Slash Commands

```
/agentic-md-export:<action> [args]
```

### Via CLI

```bash
./run tool/md_export_api.py <action> [args]
./run tool/md_export_api.py --help
```

## Skills

This plugin includes auto-triggered skills that activate when you describe related tasks.
Claude will automatically use the appropriate procedures when you ask about:
- Export markdown to Google Docs and Word documents with Mermaid diagram rendering

## License

MIT

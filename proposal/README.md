# agentic-proposal

Generate sales proposals and create Google Slides presentations from templates

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

- `/agentic-proposal:*` - See available commands with `/help`

## Environment Variables

- `GOOGLE_SLIDES_TEMPLATE_ID`

## Usage

### Via Slash Commands

```
/agentic-proposal:<action> [args]
```

### Via CLI

```bash
./run tool/proposal_api.py <action> [args]
./run tool/proposal_api.py --help
```

## Skills

This plugin includes auto-triggered skills that activate when you describe related tasks.
Claude will automatically use the appropriate procedures when you ask about:
- Generate sales proposals and create Google Slides presentations from templates

## License

MIT

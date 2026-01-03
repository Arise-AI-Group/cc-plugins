# agentic-diagrams

Generate diagrams in Draw.io, Mermaid, and ASCII formats from JSON or natural language

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

- `/agentic-diagrams:*` - See available commands with `/help`

## Environment Variables

- `OPENAI_API_KEY`

## Usage

### Via Slash Commands

```
/agentic-diagrams:<action> [args]
```

### Via CLI

```bash
./run tool/diagrams_api.py <action> [args]
./run tool/diagrams_api.py --help
```

## Skills

This plugin includes auto-triggered skills that activate when you describe related tasks.
Claude will automatically use the appropriate procedures when you ask about:
- Generate diagrams in Draw.io, Mermaid, and ASCII formats from JSON or natural language

## License

MIT

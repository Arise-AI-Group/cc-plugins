# agentic-sop

Audio transcription and SOP extraction - convert interviews and recordings into structured procedures

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

- `/agentic-sop:*` - See available commands with `/help`

## Environment Variables

- `OPENAI_API_KEY`

## Usage

### Via Slash Commands

```
/agentic-sop:<action> [args]
```

### Via CLI

```bash
./run tool/sop_api.py <action> [args]
./run tool/sop_api.py --help
```

## Skills

This plugin includes auto-triggered skills that activate when you describe related tasks.
Claude will automatically use the appropriate procedures when you ask about:
- Audio transcription and SOP extraction - convert interviews and recordings into structured procedures

## License

MIT

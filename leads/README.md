# agentic-leads

Scrape and verify sales leads via Apify, upload to Google Sheets

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

- `/agentic-leads:*` - See available commands with `/help`

## Environment Variables

- `APIFY_TOKEN`

## Usage

### Via Slash Commands

```
/agentic-leads:<action> [args]
```

### Via CLI

```bash
./run tool/leads_api.py <action> [args]
./run tool/leads_api.py --help
```

## Skills

This plugin includes auto-triggered skills that activate when you describe related tasks.
Claude will automatically use the appropriate procedures when you ask about:
- Scrape and verify sales leads via Apify, upload to Google Sheets

## License

MIT

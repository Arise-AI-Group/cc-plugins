# slack

Slack channel and message management - create channels, retrieve messages, manage pins, canvases, and user groups

## Installation

```bash
/plugin install slack@cc-plugins
```

## Commands

- `/slack:skills` - See available commands with `/help`

## Environment Variables

- `SLACK_BOT_TOKEN`
- `SLACK_USER_TOKEN`

## Usage

### Via Slash Commands

```
/slack:<action> [args]
```

### Via CLI

```bash
./run tool/slack_api.py <action> [args]
./run tool/slack_api.py --help
```

## Skills

This plugin includes auto-triggered skills that activate when you describe related tasks.
Claude will automatically use the appropriate procedures when you ask about:
- Slack channel and message management - create channels, retrieve messages, manage pins, canvases, and user groups

## License

MIT

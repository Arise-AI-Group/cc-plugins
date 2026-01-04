# client-onboarding

Set up Slack channels and resources for new clients

## Installation

```bash
/plugin install client-onboarding@cc-plugins
```

## Commands

- `/client-onboarding:skills` - See available commands with `/help`

## Environment Variables

- `SLACK_BOT_TOKEN`
- `SLACK_USER_TOKEN`

## Usage

### Via Slash Commands

```
/client-onboarding:<action> [args]
```

### Via CLI

```bash
./run tool/client_onboarding_api.py <action> [args]
./run tool/client_onboarding_api.py --help
```

## Skills

This plugin includes auto-triggered skills that activate when you describe related tasks.
Claude will automatically use the appropriate procedures when you ask about:
- Set up Slack channels and resources for new clients

## License

MIT

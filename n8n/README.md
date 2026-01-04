# n8n

Manage n8n workflows - list, deploy, activate, execute, and monitor

## Installation

```bash
/plugin install n8n@cc-plugins
```

## Commands

- `/n8n:skills` - See available commands with `/help`

## Environment Variables

- `N8N_API_URL`
- `N8N_API_KEY`

## Usage

### Via Slash Commands

```
/n8n:<action> [args]
```

### Via CLI

```bash
./run tool/n8n_api.py <action> [args]
./run tool/n8n_api.py --help
```

## Skills

This plugin includes auto-triggered skills that activate when you describe related tasks.
Claude will automatically use the appropriate procedures when you ask about:
- Manage n8n workflows - list, deploy, activate, execute, and monitor

## License

MIT

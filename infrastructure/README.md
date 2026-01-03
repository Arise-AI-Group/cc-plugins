# agentic-infrastructure

Manage team infrastructure with Cloudflare DNS/tunnels and Dokploy containers

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

- `/agentic-infrastructure:*` - See available commands with `/help`

## Environment Variables

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `DOKPLOY_URL`
- `DOKPLOY_API_KEY`

## Usage

### Via Slash Commands

```
/agentic-infrastructure:<action> [args]
```

### Via CLI

```bash
./run tool/infrastructure_api.py <action> [args]
./run tool/infrastructure_api.py --help
```

## Skills

This plugin includes auto-triggered skills that activate when you describe related tasks.
Claude will automatically use the appropriate procedures when you ask about:
- Manage team infrastructure with Cloudflare DNS/tunnels and Dokploy containers

## License

MIT

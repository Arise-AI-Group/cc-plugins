# demo-deploy

Deploy demo applications with GitHub integration and Traefik routing

## Installation

```bash
/plugin install demo-deploy@cc-plugins
```

## Commands

- `/demo-deploy:skills` - See available commands with `/help`

## Environment Variables

- `DOKPLOY_URL`
- `DOKPLOY_API_KEY`

## Usage

### Via Slash Commands

```
/demo-deploy:<action> [args]
```

### Via CLI

```bash
./run tool/demo_deploy_api.py <action> [args]
./run tool/demo_deploy_api.py --help
```

## Skills

This plugin includes auto-triggered skills that activate when you describe related tasks.
Claude will automatically use the appropriate procedures when you ask about:
- Deploy demo applications with GitHub integration and Traefik routing

## License

MIT

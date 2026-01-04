# ssh

Execute commands and transfer files on remote servers via SSH/SFTP

## Installation

```bash
/plugin install ssh@cc-plugins
```

## Commands

- `/ssh:skills` - See available commands with `/help`

## Environment Variables

- `SSH_KEY_PATH`
- `SSH_PASSWORD`

## Usage

### Via Slash Commands

```
/ssh:<action> [args]
```

### Via CLI

```bash
./run tool/ssh_api.py <action> [args]
./run tool/ssh_api.py --help
```

## Skills

This plugin includes auto-triggered skills that activate when you describe related tasks.
Claude will automatically use the appropriate procedures when you ask about:
- Execute commands and transfer files on remote servers via SSH/SFTP

## License

MIT

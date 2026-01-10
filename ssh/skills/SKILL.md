---
name: ssh
description: Execute commands and transfer files on remote servers via SSH/SFTP. Use when the user asks about ssh operations, management, or automation.
---

# SSH Operations Runbook

## Purpose

Execute commands and transfer files on remote servers via SSH. Use this module when you need to:
- Run shell commands on a remote server
- Upload configuration files, scripts, or data
- Download logs, backups, or other files

## Operating Principles

### Destructive Action Protocol

SSH commands run on production servers with real consequences. Before executing ANY potentially destructive action, you MUST:

1. **Identify the risk level** of the command
2. **Explicitly ask for user confirmation** describing what will happen
3. **For HIGH-RISK actions**: Ask for confirmation TWICE, separated by a summary of consequences

### Risk Classification

| Risk Level | Examples | Required Confirmations |
|------------|----------|----------------------|
| **READ-ONLY** | `ls`, `cat`, `df -h`, `ps aux`, `systemctl status` | None |
| **LOW** | `systemctl restart`, uploading configs | 1 confirmation |
| **MEDIUM** | `apt upgrade`, `chmod`, `chown`, overwriting files | 1 confirmation + state current values first |
| **HIGH** | `rm -rf`, `dd`, `mkfs`, `DROP TABLE`, stopping databases | 2 confirmations |
| **CRITICAL** | Commands affecting `/`, `/etc`, `/var` recursively; `shutdown`; `reboot` | 2 confirmations + require explicit path/target |

### Before Destructive Commands

Always:
- State exactly what the command will do in plain language
- Show the exact command you intend to run
- Identify what data could be lost or services affected
- Ask: "Do you want me to proceed with this?"

For HIGH/CRITICAL:
- After first confirmation, summarize consequences again
- Ask: "To confirm: this will [specific consequence]. Proceed?"

### Never Assume

- Never chain destructive commands without confirmation between them
- Never use wildcards (`*`, `**`) in destructive commands without explicit user approval
- Never run `rm`, `dd`, `mkfs`, or format commands based on implied intent

## When to Use vs Alternatives

| Need | Tool |
|------|------|
| Run commands on remote server | **This module** |
| Manage Cloudflare DNS/tunnels | `infrastructure` module |
| Deploy containers | `infrastructure` module (Dokploy) |
| Execute n8n workflows | `n8n` module |

## Configuration

### Environment Variables

Credentials are loaded from `~/.config/cc-plugins/.env`. At least one is required:

```bash
# In ~/.config/cc-plugins/.env
SSH_KEY_PATH=/path/to/private/key   # Preferred: SSH key authentication
SSH_PASSWORD=your_password          # Fallback: password authentication
```

### Target Format

All commands use `user@host[:port]` format:
- `root@192.168.1.50` - Default port 22
- `admin@server.local:2222` - Custom port

## Execution Tool

**Location:** `tool/ssh_client.py`

### CLI Commands

```bash
# Execute command
./run tool/ssh_client.py exec user@host "command"

# Upload file or directory
./run tool/ssh_client.py upload user@host local_path remote_path

# Download file or directory
./run tool/ssh_client.py download user@host remote_path local_path
```

### Module Usage

```python
from modules.ssh.tool.ssh_client import SSHClient

client = SSHClient()

# Execute command - returns (stdout, stderr, exit_code)
stdout, stderr, code = client.exec("root@server", "apt update && apt upgrade -y")
if code != 0:
    print(f"Command failed: {stderr}")

# Upload file
client.upload("root@server", "./config.yaml", "/etc/app/config.yaml")

# Download file
client.download("root@server", "/var/log/app.log", "./logs/app.log")
```

## Common Operations

### Server Setup

```bash
# Update packages
./run tool/ssh_client.py exec root@server "apt update && apt upgrade -y"

# Install packages
./run tool/ssh_client.py exec root@server "apt install -y nginx docker.io"

# Check disk space
./run tool/ssh_client.py exec root@server "df -h"

# Check running services
./run tool/ssh_client.py exec root@server "systemctl list-units --type=service --state=running"
```

### File Operations

```bash
# Upload config file
./run tool/ssh_client.py upload root@server ./nginx.conf /etc/nginx/nginx.conf

# Download logs
./run tool/ssh_client.py download root@server /var/log/nginx/ ./nginx-logs/

# Backup directory
./run tool/ssh_client.py download root@server /etc/app/ ./backup/app-config/
```

### Service Management

```bash
# Restart service
./run tool/ssh_client.py exec root@server "systemctl restart nginx"

# Check service status
./run tool/ssh_client.py exec root@server "systemctl status nginx"

# View logs
./run tool/ssh_client.py exec root@server "journalctl -u nginx --since '1 hour ago'"
```

## Edge Cases & Learnings

### Authentication Priority

1. SSH key (if `SSH_KEY_PATH` exists)
2. Password (fallback)

If key auth fails, it automatically tries password. Configure both for resilience.

### Large File Transfers

For very large files or directories, consider:
- Using `rsync` via exec command for resumable transfers
- Compressing before transfer: `tar czf - /path | ...`

### Interactive Commands

This module does **not** support interactive commands (sudo prompts, vim, etc.). For sudo, use:
```bash
# Configure NOPASSWD in sudoers, or
./run tool/ssh_client.py exec user@server "echo 'password' | sudo -S command"
```

### Connection Timeouts

Default timeout is 30 seconds. For slow networks or initial connections, the connection may fail. Retry if needed.

### Host Key Verification

The client automatically accepts new host keys (equivalent to `StrictHostKeyChecking=no`). This is convenient but less secure for production environments.

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | SSH not running or wrong port | Verify SSH service and port |
| `Authentication failed` | Wrong key or password | Check credentials in `.env` |
| `Permission denied` | Insufficient remote permissions | Check user permissions on server |
| `No route to host` | Network unreachable | Check network connectivity |
| `File not found` | Remote/local path doesn't exist | Verify path exists |


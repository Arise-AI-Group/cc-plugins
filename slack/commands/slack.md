# Slack Operations
> Execute Slack operations via subcommands.

## Variables
subcommand: $1
arg1: $2
arg2: $3
arg3: $4

## Subcommands

### create <name> [description]
Create a new Slack channel.
```bash
./run tools/slack_api.py channels create "$arg1" --description "$arg2"
```

### archive <channel>
Archive a Slack channel.
```bash
./run tools/slack_api.py channels archive "$arg1"
```

### summary <channel> [days]
Summarize recent messages in a channel (default: 7 days).
```bash
./run tools/slack_api.py messages summary "$arg1" --days "${arg2:-7}"
```

### list-groups
List all Slack user groups.
```bash
./run tools/slack_api.py groups list
```

### add-to-group <group> <user>
Add a user to a Slack group.
```bash
./run tools/slack_api.py groups add-member "$arg1" "$arg2"
```

## Instructions
- Parse the subcommand from $1
- Execute the appropriate command above with remaining arguments
- Report results

## Report
Summarize what was done and any relevant URLs, channel IDs, or group names.

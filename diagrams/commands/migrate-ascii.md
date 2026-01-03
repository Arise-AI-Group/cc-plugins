# Migrate ASCII

Convert ASCII flowcharts in Markdown files to Mermaid diagrams.

## Variables

- `path`: $1
- `mode`: $2

## Instructions

- Path can be a file or directory
- Mode: `--dry-run` (default) or `--apply`
- Backups are created automatically when applying changes
- Requires `OPENAI_API_KEY` environment variable

## Run

```bash
# Preview changes (default)
./run tool/migrate_ascii_to_mermaid.py "$path" --dry-run

# Apply changes
./run tool/migrate_ascii_to_mermaid.py "$path" --apply
```

## Report

- List files that contain ASCII flowcharts
- Show count of flowcharts found vs converted
- Report backup location if changes were applied

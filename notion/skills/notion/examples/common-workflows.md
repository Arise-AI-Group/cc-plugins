# Common Notion Workflows

## Create Documentation Page

```bash
# Create page with initial content
./run tool/notion_api.py pages create <docs-page-id> \
  --title "API Documentation" \
  --content-file docs/api.md \
  --icon "📚"
```

## Export Page to Markdown

```bash
./run tool/notion_api.py blocks children <page-id> --all --as-markdown > .tmp/export.md
```

## Bulk Query Database

```bash
# Get all entries with specific status
./run tool/notion_api.py databases query <db-id> --all \
  --filter '{"property": "Status", "select": {"equals": "Done"}}'
```

## Add Entry to Database

```bash
# Create page in database
./run tool/notion_api.py pages create <database-id> \
  --title "New Task" \
  --database
```

## Add Entry with Properties

```bash
./run tool/notion_api.py pages create <database-id> \
  --title "Project Task" \
  --database \
  --properties '{
    "Status": {"select": {"name": "In Progress"}},
    "Priority": {"select": {"name": "High"}},
    "Due Date": {"date": {"start": "2026-01-20"}}
  }'
```

## Bulk Import to Database

```bash
# Prepare entries.json
cat > entries.json << 'EOF'
[
  {"title": "Task 1", "properties": {"Status": {"select": {"name": "Open"}}}},
  {"title": "Task 2", "properties": {"Status": {"select": {"name": "Open"}}}},
  {"title": "Task 3", "properties": {"Priority": {"select": {"name": "High"}}}}
]
EOF

# Import
./run tool/notion_api.py pages create-batch <database-id> --file entries.json
```

## Add Schema Property to Database

```bash
# First, find the data source ID
./run tool/notion_api.py search "My Database" --filter database

# Add new property
./run tool/notion_api.py data_sources update <data_source_id> \
  --properties '{
    "Priority": {
      "select": {
        "options": [
          {"name": "High", "color": "red"},
          {"name": "Medium", "color": "yellow"},
          {"name": "Low", "color": "green"}
        ]
      }
    }
  }'
```

## Search and Update Multiple Pages

```bash
# Search for pages
./run tool/notion_api.py search "meeting notes" --filter page --limit 20

# Prepare updates.json with page IDs from search results
cat > updates.json << 'EOF'
[
  {"page_id": "abc123", "properties": {"Status": {"select": {"name": "Archived"}}}},
  {"page_id": "def456", "properties": {"Status": {"select": {"name": "Archived"}}}}
]
EOF

# Batch update
./run tool/notion_api.py pages update-batch --file updates.json
```

## Append Content After Specific Section

```bash
# First, get blocks to find the target block ID
./run tool/notion_api.py blocks children <page_id>

# Append after specific block
./run tool/notion_api.py blocks append <page_id> \
  --content "## New Section\n\nInserted after the intro." \
  --after <block_id>
```

# Notion CLI Reference

## Page Operations

### Get Page
```bash
./run tool/notion_api.py pages get <page_id>
```

### Create Page
```bash
# Create page under another page
./run tool/notion_api.py pages create <parent_page_id> \
  --title "New Page Title" \
  --content "# Heading\n\nParagraph content" \
  --icon "📄"

# Create page in a database
./run tool/notion_api.py pages create <database_id> \
  --title "New Entry" \
  --database

# Create database entry with properties
./run tool/notion_api.py pages create <database_id> \
  --title "New Task" \
  --database \
  --properties '{
    "Status": {"select": {"name": "Open"}},
    "Priority": {"select": {"name": "High"}},
    "Project": {"relation": [{"id": "project-page-id"}]}
  }'

# Create from markdown file
./run tool/notion_api.py pages create <parent_id> \
  --title "Documentation" \
  --content-file .tmp/content.md
```

### Update Page
```bash
./run tool/notion_api.py pages update <page_id> --title "New Title"
./run tool/notion_api.py pages update <page_id> --icon "✅"
```

### Archive/Restore
```bash
./run tool/notion_api.py pages archive <page_id>
./run tool/notion_api.py pages restore <page_id>
```

---

## Database Operations

### Query Database
```bash
# Get entries (default: 100)
./run tool/notion_api.py databases query <database_id>

# Get ALL entries (paginated)
./run tool/notion_api.py databases query <database_id> --all

# With filter
./run tool/notion_api.py databases query <database_id> \
  --filter '{"property": "Status", "select": {"equals": "Active"}}'

# With sorting
./run tool/notion_api.py databases query <database_id> \
  --sorts '[{"property": "Created", "direction": "descending"}]'
```

### Get Database Schema
```bash
./run tool/notion_api.py databases get <database_id>
```

### Create Database
```bash
./run tool/notion_api.py databases create <parent_page_id> \
  --title "Project Tracker" \
  --properties '{
    "Name": {"title": {}},
    "Status": {"select": {"options": [{"name": "Not Started"}, {"name": "In Progress"}, {"name": "Done"}]}},
    "Due Date": {"date": {}}
  }'
```

---

## Data Source Operations

### Get Data Source
```bash
./run tool/notion_api.py data_sources get <data_source_id>
```

### Update Data Source Schema
```bash
# Add properties to a database
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

# Add a relation property
./run tool/notion_api.py data_sources update <data_source_id> \
  --properties '{
    "Project": {
      "relation": {
        "data_source_id": "<target_data_source_id>",
        "type": "dual_property",
        "dual_property": {"synced_property_name": "Related Items"}
      }
    }
  }'
```

---

## Block Operations

### Get Page Content
```bash
# Get as JSON
./run tool/notion_api.py blocks children <page_id>

# Get ALL blocks (paginated)
./run tool/notion_api.py blocks children <page_id> --all

# Get ALL blocks recursively (includes nested content)
./run tool/notion_api.py blocks children <page_id> --recursive

# Get as markdown
./run tool/notion_api.py blocks children <page_id> --as-markdown
```

### Append Content
```bash
# Append markdown (at end of page)
./run tool/notion_api.py blocks append <page_id> \
  --content "## New Section\n\nAdded paragraph."

# Insert after a specific block
./run tool/notion_api.py blocks append <page_id> \
  --content "Inserted content" \
  --after <block_id>

# Append from file
./run tool/notion_api.py blocks append <page_id> \
  --content-file .tmp/additional_content.md

# Append raw JSON blocks
./run tool/notion_api.py blocks append <page_id> \
  --json '[{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "Hello"}}]}}]'
```

### Update Block
```bash
# Update block text content
./run tool/notion_api.py blocks update <block_id> \
  --type paragraph \
  --content "Updated text content"

# Update heading
./run tool/notion_api.py blocks update <block_id> \
  --type heading_2 \
  --content "New Heading Text"

# Update with full JSON
./run tool/notion_api.py blocks update <block_id> \
  --type paragraph \
  --json '{"paragraph": {"rich_text": [{"type": "text", "text": {"content": "Bold text"}, "annotations": {"bold": true}}]}}'
```

### Delete Block
```bash
./run tool/notion_api.py blocks delete <block_id>
```

---

## Comments

```bash
# List comments on a page
./run tool/notion_api.py comments list <page_id>

# Create a comment
./run tool/notion_api.py comments create <page_id> --content "This is my comment"

# Reply to thread
./run tool/notion_api.py comments create <page_id> \
  --content "Reply to thread" \
  --discussion <discussion_id>
```

---

## Batch Operations

### Create Multiple Database Entries
```bash
# From JSON file
./run tool/notion_api.py pages create-batch <database_id> --file entries.json

# From inline JSON
./run tool/notion_api.py pages create-batch <database_id> --json '[
  {"title": "Task 1", "properties": {"Status": {"select": {"name": "Open"}}}},
  {"title": "Task 2", "properties": {"Priority": {"select": {"name": "High"}}}}
]'
```

**Entry format:**
```json
[
  {
    "title": "Entry Name",
    "properties": {"Status": {"select": {"name": "Open"}}},
    "content": "## Page Body\nOptional markdown content",
    "icon": "📌"
  }
]
```

### Update Multiple Pages
```bash
./run tool/notion_api.py pages update-batch --file updates.json
./run tool/notion_api.py pages update-batch --json '[
  {"page_id": "id1", "properties": {"Status": {"select": {"name": "Done"}}}},
  {"page_id": "id2", "icon": "✅"}
]'
```

### Delete Multiple Blocks
```bash
./run tool/notion_api.py blocks delete-batch <id1> <id2> <id3>
```

### Batch Response Format
```json
{
  "created": [...],
  "failed": [{"index": 0, "entry": {...}, "error": "Error message"}],
  "total": 10,
  "success_count": 9,
  "failure_count": 1
}
```

---

## Search

```bash
# Search everything
./run tool/notion_api.py search "project documentation"

# Search only pages
./run tool/notion_api.py search "meeting notes" --filter page

# Search only databases
./run tool/notion_api.py search "tracker" --filter database

# Limit results
./run tool/notion_api.py search "notes" --limit 10
```

---

## Users

```bash
# List all users
./run tool/notion_api.py users list

# Get bot info
./run tool/notion_api.py users me

# Get specific user
./run tool/notion_api.py users get <user_id>
```

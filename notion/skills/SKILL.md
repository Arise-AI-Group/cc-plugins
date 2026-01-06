---
name: notion
description: Notion page, database, and block management - create pages, query databases, manage content blocks, and search workspace. Use when the user asks about notion operations, management, or automation.
---

# Notion Management

## Execution Method
**Always use Python**: `tool/notion_api.py`

## Purpose
Manage Notion pages, databases, and content blocks via the API. Use this for
documentation management, knowledge base operations, project tracking databases,
and workspace search.

## When to Use This Directive

**Trigger phrases:**
- "Create a Notion page for..."
- "Add content to the Notion page"
- "Query the project database"
- "Search Notion for..."
- "Archive the old documentation"
- "Update the database entry"
- "List items in the Notion database"
- "Export page content"

## Execution Tools

**Location:** `tool/notion_api.py`

---

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

**IMPORTANT:** Notion now uses a `data_sources` architecture separate from `databases`.
For adding or modifying database properties (schema changes), use `data_sources update`
instead of `databases update`. The legacy endpoint often fails silently.

### Get Data Source
```bash
# Get full schema including all properties
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

# Add a relation property (requires target data_source_id, not database_id)
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

### Finding Data Source IDs
Data source IDs are different from database IDs. To find a data source ID:
```bash
# Search returns data_source objects with their IDs
./run tool/notion_api.py search "database name" --filter database
```
The `id` field in the returned `data_source` object is the data source ID.

---

## Block Operations

### Get Page Content
```bash
# Get as JSON
./run tool/notion_api.py blocks children <page_id>

# Get ALL blocks (paginated)
./run tool/notion_api.py blocks children <page_id> --all

# Get as markdown
./run tool/notion_api.py blocks children <page_id> --as-markdown
```

### Append Content
```bash
# Append markdown
./run tool/notion_api.py blocks append <page_id> \
  --content "## New Section\n\nAdded paragraph."

# Append from file
./run tool/notion_api.py blocks append <page_id> \
  --content-file .tmp/additional_content.md

# Append raw JSON blocks
./run tool/notion_api.py blocks append <page_id> \
  --json '[{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "Hello"}}]}}]'
```

### Delete Block
```bash
./run tool/notion_api.py blocks delete <block_id>
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

---

## Module Usage

```python
from modules.notion.tool.notion_api import NotionClient

client = NotionClient()

# Search
results = client.search("project", filter_type="page")

# Get page
page = client.get_page("page-id-here")

# Query database
entries = client.query_database_all("db-id", filter={
    "property": "Status",
    "select": {"equals": "Active"}
})

# Create page with content
blocks = client.markdown_to_blocks("# Title\n\nContent here")
page = client.create_page("parent-id", "My Page", children=blocks)

# Get page content as markdown
blocks = client.get_all_block_children("page-id")
markdown = client.blocks_to_markdown(blocks)
```

---

## Environment Variables

Required in `.env`:
```
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Getting Your API Key

1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Name it (e.g., "Agentic Workspace")
4. Select the workspace
5. Set capabilities: Read content, Update content, Insert content
6. Copy the "Internal Integration Secret"
7. Add pages/databases to the integration:
   - Open the page in Notion
   - Click "..." menu > "Add connections"
   - Select your integration

---

## Edge Cases & Learnings

### Access Control
- The integration can only access pages explicitly shared with it
- Share parent pages to grant access to child pages
- Database entries inherit access from the database

### Rate Limits
- Notion API: ~3 requests/second average
- The client raises `NotionRateLimitError` on 429 responses
- Add retry logic for high-volume operations

### IDs
- All Notion IDs are UUIDs (with or without dashes)
- Pages, databases, and blocks all use the same ID format
- A page ID can also be used as a block ID

### Content Blocks
- Block types: paragraph, heading_1/2/3, bulleted_list_item,
  numbered_list_item, code, quote, callout, divider, toggle, to_do
- Some block types have children (toggle, column_list)
- The markdown converter handles common types
- For complex layouts, use raw JSON blocks

### API Limitations (Cannot Create via API)
- **Status property type** - Cannot create databases with `status` property via API.
  Use `select` instead and convert to status manually in the Notion UI if needed.
- **Linked database views** - Embedded views of existing databases with filters
  cannot be created through the API. You can only create NEW databases via
  the `databases create` endpoint. Linked views require Notion UI.
- **Button blocks** - Template buttons with pre-filled values are UI-only
- **Synced blocks** - Can read but not create or update synced content
- **Link previews** - Only returned in responses, cannot be created
- **Template blocks** - Deprecated as of March 2023
- **Code block preview mode** - The "preview only" toggle for Mermaid/math blocks
  is not exposed via API. Code blocks always show code; preview-only requires UI.

### Data Sources vs Databases
Notion's API has evolved to use a `data_sources` architecture:
- **databases.create** - Still works for creating new databases
- **databases.update** - DEPRECATED for schema changes (adding properties). Often
  returns success but doesn't actually apply the changes.
- **data_sources.query** - Used for querying database entries (the plugin already uses this)
- **data_sources.update** - The CORRECT endpoint for modifying database schemas
- **Relations** - Must use `data_source_id` not `database_id` when creating relations

**Workflow for adding properties to an existing database:**
1. Find the data source ID: `search "database name" --filter database`
2. Update schema: `data_sources update <data_source_id> --properties '{...}'`

For dashboards with linked database views, use the API to create the page
structure (headings, sections, instructions) and have users add the linked
databases manually via Notion UI using `/linked` command.

### Database Properties
- Common types: title, rich_text, number, select, multi_select,
  date, checkbox, url, email, phone_number, formula, relation, rollup
- The "Name" or "Title" property is required for all database entries
- Filter syntax: https://developers.notion.com/reference/post-database-query-filter

### Pagination
- List operations return max 100 items
- Use `--all` flag to auto-paginate
- Or manually use `start_cursor` and `has_more` in Python

### Markdown Conversion
The `markdown_to_blocks()` helper supports:
- Headings: `# ## ###`
- Lists: `- ` bullets, `1.` numbered
- Checkboxes: `- [ ]` and `- [x]`
- Code blocks: triple backticks with language
- Quotes: `>`
- Dividers: `---`

**Not supported** (create with JSON instead):
- **Tables** - Markdown tables render as plain text. Use Notion `table` + `table_row` blocks
- **Images** - Use `image` block type with URL

---

## Common Workflows

### Create Documentation Page
```bash
# Create page with initial content
./run tool/notion_api.py pages create <docs-page-id> \
  --title "API Documentation" \
  --content-file docs/api.md \
  --icon "📚"
```

### Export Page to Markdown
```bash
./run tool/notion_api.py blocks children <page-id> --all --as-markdown > .tmp/export.md
```

### Bulk Query Database
```bash
# Get all entries with specific status
./run tool/notion_api.py databases query <db-id> --all \
  --filter '{"property": "Status", "select": {"equals": "Done"}}'
```

### Add Entry to Database
```bash
# Create page in database
./run tool/notion_api.py pages create <database-id> \
  --title "New Task" \
  --database
```

---

## Filter Examples

### Select Property
```json
{"property": "Status", "select": {"equals": "Active"}}
```

### Checkbox Property
```json
{"property": "Done", "checkbox": {"equals": true}}
```

### Date Property
```json
{"property": "Due Date", "date": {"on_or_before": "2024-12-31"}}
```

### Text Contains
```json
{"property": "Name", "rich_text": {"contains": "project"}}
```

### Compound Filter (AND)
```json
{
  "and": [
    {"property": "Status", "select": {"equals": "Active"}},
    {"property": "Assignee", "people": {"contains": "user-id"}}
  ]
}
```

### Compound Filter (OR)
```json
{
  "or": [
    {"property": "Status", "select": {"equals": "Active"}},
    {"property": "Status", "select": {"equals": "In Progress"}}
  ]
}
```

---

## Sort Examples

```json
[{"property": "Created time", "direction": "descending"}]
```

```json
[
  {"property": "Priority", "direction": "descending"},
  {"property": "Name", "direction": "ascending"}
]
```

---

## Changelog

### 2026-01-06
- **Added:** `data_sources` CLI commands for schema modifications:
  - `data_sources get <data_source_id>` - Retrieve full schema
  - `data_sources update <data_source_id> --properties JSON` - Add/modify properties
- **Added:** `get_data_source()` and `update_data_source()` methods to NotionClient
- **Documented:** Data Sources vs Databases architecture explanation in Edge Cases
- **Note:** `databases update` is now marked as legacy - use `data_sources update` for
  schema changes as the databases.update endpoint often fails silently.

### 2025-12-30
- **Fixed:** `create_database()` now includes required `type` field in parent object.
  The Notion API requires `{"type": "page_id", "page_id": "..."}` format for parent,
  not just `{"page_id": "..."}`. This was causing "body.parent.type should be defined"
  errors when creating databases via CLI.
- **Added:** `databases update` CLI command to update database title and properties.
  Usage: `./run tool/notion_api.py databases update <db_id> --properties '{...}'`


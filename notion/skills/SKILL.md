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

# Get ALL blocks recursively (includes nested content in toggles, columns, etc.)
./run tool/notion_api.py blocks children <page_id> --recursive

# Get as markdown
./run tool/notion_api.py blocks children <page_id> --as-markdown
```

### Append Content
```bash
# Append markdown (at end of page)
./run tool/notion_api.py blocks append <page_id> \
  --content "## New Section\n\nAdded paragraph."

# Insert after a specific block (use --after to control position)
./run tool/notion_api.py blocks append <page_id> \
  --content "Inserted content" \
  --after <block_id>

# Append from file
./run tool/notion_api.py blocks append <page_id> \
  --content-file .tmp/additional_content.md

# Append raw JSON blocks
./run tool/notion_api.py blocks append <page_id> \
  --json '[{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "Hello"}}]}}]'

# Insert JSON blocks at specific position
./run tool/notion_api.py blocks append <page_id> \
  --json '[...]' \
  --after <block_id>
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

# Update with full JSON (for complex updates)
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

# Create a comment on a page
./run tool/notion_api.py comments create <page_id> --content "This is my comment"

# Reply to an existing discussion thread
./run tool/notion_api.py comments create <page_id> \
  --content "Reply to thread" \
  --discussion <discussion_id>
```

---

## Batch Operations

Batch operations handle multiple items with built-in rate limiting (~3 req/sec) and partial failure handling.

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
# From JSON file
./run tool/notion_api.py pages update-batch --file updates.json

# From inline JSON
./run tool/notion_api.py pages update-batch --json '[
  {"page_id": "id1", "properties": {"Status": {"select": {"name": "Done"}}}},
  {"page_id": "id2", "icon": "✅"}
]'
```

**Update format:**
```json
[
  {
    "page_id": "page-id-here",
    "properties": {"Status": {"select": {"name": "Done"}}},
    "icon": "✅",
    "archived": false
  }
]
```

### Delete Multiple Blocks
```bash
./run tool/notion_api.py blocks delete-batch <id1> <id2> <id3>
```

### Batch Response Format
All batch operations return:
```json
{
  "created": [...],      // or "updated" or "deleted"
  "failed": [
    {"index": 0, "entry": {...}, "error": "Error message"}
  ],
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

# Get nested content (toggles, columns, etc.)
blocks = client.get_all_block_children_recursive("page-id")

# Create database entry with properties (using helpers)
page = client.create_page(
    parent_id="db-id",
    title="New Task",
    properties={
        "Status": client.prop_select("Open"),
        "Priority": client.prop_select("High"),
        "Project": client.prop_relation(["project-id"]),
        "Due Date": client.prop_date("2026-01-15"),
        "Complete": client.prop_checkbox(False),
    },
    parent_type="database"
)

# Update a block
client.update_block("block-id", {
    "paragraph": {
        "rich_text": [{"type": "text", "text": {"content": "Updated content"}}]
    }
})

# Comments
comments = client.list_comments("page-id")
client.create_comment("page-id", "This is a comment")

# Batch operations with progress callback
def on_progress(current, total, result):
    print(f"[{current}/{total}] {'✓' if result['success'] else '✗'}")

# Create multiple entries
entries = [
    {"title": "Task 1", "properties": {"Status": client.prop_select("Open")}},
    {"title": "Task 2", "properties": {"Priority": client.prop_select("High")}},
]
result = client.create_pages_batch("db-id", entries, on_progress=on_progress)
print(f"Created: {result['success_count']}, Failed: {result['failure_count']}")

# Update multiple pages
updates = [
    {"page_id": "id1", "properties": {"Status": client.prop_select("Done")}},
    {"page_id": "id2", "icon": "✅"},
]
result = client.update_pages_batch(updates)

# Delete multiple blocks
result = client.delete_blocks_batch(["block-id-1", "block-id-2", "block-id-3"])
```

### Property Helpers
For Python module usage, these helpers simplify property value construction:

```python
client.prop_title("Title text")      # title property
client.prop_text("Rich text")        # rich_text property
client.prop_select("Option")         # select property
client.prop_multi_select(["A", "B"]) # multi_select property
client.prop_date("2026-01-15")       # date property (ISO 8601)
client.prop_relation(["id1", "id2"]) # relation property
client.prop_checkbox(True)           # checkbox property
client.prop_number(42.5)             # number property
client.prop_url("https://...")       # url property
client.prop_email("user@example.com")# email property
client.prop_phone("+1234567890")     # phone_number property
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
- Tables: `| col | col |` with header row support
- **Inline formatting:**
  - `**bold**` → bold text
  - `*italic*` → italic text
  - `` `code` `` → inline code
  - `~~strikethrough~~` → strikethrough text
  - `[text](url)` → hyperlinks

**Not supported** (create with JSON instead):
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

### 2026-01-08 (continued)
- **Added:** Markdown table support in `markdown_to_blocks()`:
  - Tables with `| col | col |` syntax are now converted to native Notion table blocks
  - Header rows detected automatically (when followed by `|---|---|` separator)
  - Inline formatting (bold, italic, links) works within table cells
- **Added:** Batch operations for bulk imports and updates:
  - `pages create-batch <db_id> --file entries.json` - Create multiple database entries
  - `pages update-batch --file updates.json` - Update multiple pages
  - `blocks delete-batch <id1> <id2>...` - Delete multiple blocks
- **Feature:** Built-in rate limiting (~3 requests/second) for batch operations
- **Feature:** Partial failure handling - operations continue on error with detailed failure reports
- **Added:** Python methods: `create_pages_batch()`, `update_pages_batch()`, `delete_blocks_batch()`

### 2026-01-08
- **Added:** `blocks update` command to edit existing blocks:
  `./run tool/notion_api.py blocks update <block_id> --type paragraph --content "New text"`
- **Added:** `--recursive` flag to `blocks children` for fetching nested content (toggles, columns):
  `./run tool/notion_api.py blocks children <page_id> --recursive`
- **Added:** `comments` commands for listing and creating comments:
  - `./run tool/notion_api.py comments list <page_id>`
  - `./run tool/notion_api.py comments create <page_id> --content "Comment text"`
- **Added:** `--properties` flag to `pages create` for setting database entry properties:
  `./run tool/notion_api.py pages create <db_id> --database --title "Task" --properties '{...}'`
- **Enhanced:** Inline markdown parsing now supports `**bold**`, `*italic*`, `` `code` ``,
  and `~~strikethrough~~` with proper Notion annotations (no more asterisks showing in output)
- **Added:** Property helper methods for Python module: `prop_select()`, `prop_relation()`,
  `prop_date()`, `prop_checkbox()`, `prop_number()`, `prop_url()`, `prop_email()`, `prop_phone()`

### 2026-01-09
- **Added:** `--after <block_id>` parameter to `blocks append` command. Allows inserting
  blocks after a specific block instead of always appending to the end of the page.
  Usage: `./run tool/notion_api.py blocks append <page_id> --content "..." --after <block_id>`

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


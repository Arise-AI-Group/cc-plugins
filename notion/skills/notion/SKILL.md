---
name: notion
description: This skill should be used when the user asks to "create a Notion page", "query the database", "add content to Notion", "search Notion for", "export page content", "update database entry". Provides Notion API integration for pages, databases, blocks, and search.
---

# Notion Management

## Execution Method

**Always use Python**: `tool/notion_api.py`

Do NOT use n8n MCP tools for Notion operations unless user explicitly requests n8n workflow development.

## Purpose

Manage Notion pages, databases, and content blocks via the API. Use this for documentation management, knowledge base operations, project tracking databases, and workspace search.

## Trigger Phrases

- "Create a Notion page for..."
- "Add content to the Notion page"
- "Query the project database"
- "Search Notion for..."
- "Archive the old documentation"
- "Update the database entry"
- "List items in the Notion database"
- "Export page content"

---

## Task Management → Use Tasks Plugin

**IMPORTANT:** For task management operations, prefer the **Tasks plugin** if installed.

**Task-related phrases that should use Tasks plugin:**
- "Create a task for...", "Add a to-do...", "Assign X to Y"
- "Query my tasks", "Show tasks assigned to..."
- "Update the task...", "Mark task as done"
- "Prioritize my day", "What's due today/this week"

**Why use Tasks plugin:**
- Field validation and interactive prompting
- User/project resolution (names to Notion IDs)
- Priority normalization ("p1", "high", "urgent")
- Date parsing ("tomorrow", "Friday", "next week")

**When to use Notion plugin instead:**
- General database operations (non-task databases)
- Page creation/editing
- Block manipulation
- Search operations

---

## Core Operations

### Page Operations

```bash
# Get page
./run tool/notion_api.py pages get <page_id>

# Create page under another page
./run tool/notion_api.py pages create <parent_page_id> \
  --title "New Page Title" \
  --content "# Heading\n\nParagraph content"

# Create database entry with properties
./run tool/notion_api.py pages create <database_id> \
  --title "New Task" \
  --database \
  --properties '{"Status": {"select": {"name": "Open"}}}'

# Archive/restore
./run tool/notion_api.py pages archive <page_id>
./run tool/notion_api.py pages restore <page_id>
```

### Database Operations

```bash
# Query database
./run tool/notion_api.py databases query <database_id>
./run tool/notion_api.py databases query <database_id> --all  # paginated

# With filter
./run tool/notion_api.py databases query <database_id> \
  --filter '{"property": "Status", "select": {"equals": "Active"}}'

# Get schema
./run tool/notion_api.py databases get <database_id>
```

### Block Operations

```bash
# Get page content
./run tool/notion_api.py blocks children <page_id>
./run tool/notion_api.py blocks children <page_id> --as-markdown
./run tool/notion_api.py blocks children <page_id> --recursive

# Append content
./run tool/notion_api.py blocks append <page_id> --content "## New Section"
./run tool/notion_api.py blocks append <page_id> --content "..." --after <block_id>

# Update/delete block
./run tool/notion_api.py blocks update <block_id> --type paragraph --content "Updated"
./run tool/notion_api.py blocks delete <block_id>
```

### Search

```bash
./run tool/notion_api.py search "query"
./run tool/notion_api.py search "query" --filter page
./run tool/notion_api.py search "query" --filter database
```

For exhaustive CLI commands, see [references/cli-reference.md](references/cli-reference.md).

---

## Data Source Operations

**IMPORTANT:** For adding or modifying database properties (schema changes), use `data_sources update` instead of `databases update`. The legacy endpoint often fails silently.

```bash
# Get full schema
./run tool/notion_api.py data_sources get <data_source_id>

# Add properties
./run tool/notion_api.py data_sources update <data_source_id> \
  --properties '{"Priority": {"select": {"options": [{"name": "High"}]}}}'
```

For details on data sources vs databases, see [references/api-limitations.md](references/api-limitations.md).

---

## Environment Variables

Required in `~/.config/cc-plugins/.env`:

```
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Getting Your API Key

1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Name it, select workspace, set capabilities
4. Copy the "Internal Integration Secret"
5. Share pages/databases with the integration via "Add connections"

---

## Additional Resources

- [references/cli-reference.md](references/cli-reference.md) - Exhaustive CLI commands
- [references/filters-and-sorts.md](references/filters-and-sorts.md) - Filter/sort JSON examples
- [references/api-limitations.md](references/api-limitations.md) - Edge cases, data sources vs databases
- [references/module-usage.md](references/module-usage.md) - Python module examples
- [examples/common-workflows.md](examples/common-workflows.md) - Common workflow patterns

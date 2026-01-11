# Notion API Limitations & Edge Cases

## Access Control

- The integration can only access pages explicitly shared with it
- Share parent pages to grant access to child pages
- Database entries inherit access from the database

## Rate Limits

- Notion API: ~3 requests/second average
- The client raises `NotionRateLimitError` on 429 responses
- Add retry logic for high-volume operations

## IDs

- All Notion IDs are UUIDs (with or without dashes)
- Pages, databases, and blocks all use the same ID format
- A page ID can also be used as a block ID

---

## API Limitations (Cannot Create via API)

- **Status property type** - Cannot create databases with `status` property via API. Use `select` instead and convert to status manually in the Notion UI if needed.
- **Linked database views** - Embedded views of existing databases with filters cannot be created through the API. You can only create NEW databases.
- **Button blocks** - Template buttons with pre-filled values are UI-only
- **Synced blocks** - Can read but not create or update synced content
- **Link previews** - Only returned in responses, cannot be created
- **Template blocks** - Deprecated as of March 2023
- **Code block preview mode** - The "preview only" toggle for Mermaid/math blocks is not exposed via API.

---

## Data Sources vs Databases

Notion's API has evolved to use a `data_sources` architecture:

- **databases.create** - Still works for creating new databases
- **databases.update** - DEPRECATED for schema changes (adding properties). Often returns success but doesn't actually apply the changes.
- **data_sources.query** - Used for querying database entries
- **data_sources.update** - The CORRECT endpoint for modifying database schemas
- **Relations** - Must use `data_source_id` not `database_id` when creating relations

**Workflow for adding properties to an existing database:**
1. Find the data source ID: `search "database name" --filter database`
2. Update schema: `data_sources update <data_source_id> --properties '{...}'`

For dashboards with linked database views, use the API to create the page structure (headings, sections) and have users add linked databases manually via Notion UI.

---

## Content Blocks

- Block types: paragraph, heading_1/2/3, bulleted_list_item, numbered_list_item, code, quote, callout, divider, toggle, to_do
- Some block types have children (toggle, column_list)
- The markdown converter handles common types
- For complex layouts, use raw JSON blocks

---

## Markdown Conversion

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

## Pagination

- List operations return max 100 items
- Use `--all` flag to auto-paginate
- Or manually use `start_cursor` and `has_more` in Python

---

## Changelog

### 2026-01-09
- **Added:** `--after <block_id>` parameter to `blocks append` command

### 2026-01-08
- **Added:** Markdown table support in `markdown_to_blocks()`
- **Added:** Batch operations for bulk imports and updates
- **Added:** `blocks update` command to edit existing blocks
- **Added:** `--recursive` flag to `blocks children`
- **Added:** `comments` commands
- **Added:** `--properties` flag to `pages create`
- **Enhanced:** Inline markdown parsing with proper annotations

### 2026-01-06
- **Added:** `data_sources` CLI commands for schema modifications
- **Documented:** Data Sources vs Databases architecture

### 2025-12-30
- **Fixed:** `create_database()` now includes required `type` field in parent object
- **Added:** `databases update` CLI command

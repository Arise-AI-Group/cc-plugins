# Notion Python Module Usage

## Basic Usage

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
```

---

## Creating Database Entries

```python
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
```

---

## Property Helpers

These helpers simplify property value construction:

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

## Updating Blocks

```python
# Update a block
client.update_block("block-id", {
    "paragraph": {
        "rich_text": [{"type": "text", "text": {"content": "Updated content"}}]
    }
})
```

---

## Comments

```python
# List comments
comments = client.list_comments("page-id")

# Create comment
client.create_comment("page-id", "This is a comment")
```

---

## Batch Operations

```python
# Progress callback
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

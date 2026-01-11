# Notion Filters and Sorts Reference

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

### Single Sort
```json
[{"property": "Created time", "direction": "descending"}]
```

### Multiple Sorts
```json
[
  {"property": "Priority", "direction": "descending"},
  {"property": "Name", "direction": "ascending"}
]
```

---

## Usage with CLI

```bash
# Query with filter
./run tool/notion_api.py databases query <database_id> \
  --filter '{"property": "Status", "select": {"equals": "Active"}}'

# Query with sort
./run tool/notion_api.py databases query <database_id> \
  --sorts '[{"property": "Created time", "direction": "descending"}]'

# Combined filter and sort
./run tool/notion_api.py databases query <database_id> \
  --filter '{"property": "Done", "checkbox": {"equals": false}}' \
  --sorts '[{"property": "Due Date", "direction": "ascending"}]'
```

---

## Filter Reference

Full filter syntax documentation: https://developers.notion.com/reference/post-database-query-filter

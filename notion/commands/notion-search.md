# Notion Search

Quick search across Notion workspace for pages and databases.

## Arguments
- `$ARGUMENTS`: Search query (e.g., "project docs", "meeting notes")

## Usage
```
/notion-search project documentation
/notion-search meeting notes
/notion-search tracker
```

## Instructions

1. Run the search command:
```bash
./run tool/notion_api.py search "$ARGUMENTS" --limit 10
```

2. Parse the JSON results and format as a table:
   - Title
   - Type (page/database)
   - Last edited
   - ID (for reference)

3. If no results found, suggest:
   - Check if the page is shared with the integration
   - Try broader search terms

## Report Format

Present results as:

| Title | Type | Last Edited |
|-------|------|-------------|
| Project Docs | page | 2024-01-15 |
| Task Tracker | database | 2024-01-14 |

Include the page/database IDs for follow-up operations.

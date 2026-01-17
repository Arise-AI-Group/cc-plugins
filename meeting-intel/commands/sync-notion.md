---
name: sync-notion
description: Fetch known entities from Notion Agency OS to prioritize matching during transcript processing
---

# Sync Notion Entities

Fetch existing entities from Notion Agency OS databases and cache them locally for entity resolution priority.

## Usage

```
/meeting-intel:sync-notion
```

## Purpose

When processing meeting transcripts, we want to:
1. **Match existing Notion entities** rather than creating duplicates
2. **Link local entities to Notion IDs** for future sync
3. **Prioritize established entities** over creating new ones

## Notion Databases

Fetch from these Agency OS databases:

| Entity Type | Database | Database ID | Filter |
|-------------|----------|-------------|--------|
| Companies | Companies | `2d7e7406-6c7d-81bd-a74b-eeb28c4aadc9` | Type in (Lead, Client) |
| Contacts | Contacts | `2d5e7406-6c7d-81d3-ae7c-c375989f3bb0` | Has Company relation |
| Projects | Projects | `2d5e7406-6c7d-81d7-b1f4-e7315c28b8f8` | Status != "Completed" |
| Topics | Topics | `2d6e7406-6c7d-819b-ab0f-dc943ee66193` | All |
| Use Cases | Use Cases | `c4a44851-ff8d-4177-8b16-a294f3cbf7fe` | Status != "Resolved" |
| Issues | Issues | `67354cb6-1234-4327-8839-8c7db20a089c` | Status = "Open" |

## Workflow

### 1. Query Notion Databases
Use the Notion plugin to query each database:

```
# Companies
Query Companies database with filter: Type in ["Lead", "Client"]
Extract: Name, Type, Industry, Website

# Contacts
Query Contacts database
Extract: Client Name (title), Email, Company (relation), Role

# Projects
Query Projects database with filter: Status != "Completed"
Extract: Project Name, Company (relation), Status, Manager

# Topics
Query Topics database (all)
Extract: Name, Category, Description

# Use Cases
Query Use Cases database with filter: Status != "Resolved"
Extract: Name, Project (relation), Status, Priority

# Issues
Query Issues database with filter: Status = "Open"
Extract: Name, Type, Project (relation), Status, Owner
```

### 2. Create Notion Cache
Write results to `./knowledge/notion-cache.md`:

```markdown
---
synced: 2025-01-17T10:30:00Z
---

# Notion Entity Cache

This cache is used by meeting-intel to prioritize matching against existing Notion entities.

## Companies
| Name | Notion ID | Type | Industry |
|------|-----------|------|----------|
| Vioxx | abc-123 | Lead | Software |
| Morningside | def-456 | Client | Consulting |

## Contacts
| Name | Email | Company | Role | Notion ID |
|------|-------|---------|------|-----------|
| Brandon Smith | brandon@vioxx.com | Vioxx | CEO | ghi-789 |
| Sarah Jones | sarah@morningside.com | Morningside | PM | jkl-012 |

## Projects
| Name | Company | Status | Notion ID |
|------|---------|--------|-----------|
| Document Extraction | Vioxx | In Progress | mno-345 |
| Internal Tools | Morningside | Active | pqr-678 |

## Topics
| Name | Category | Notion ID |
|------|----------|-----------|
| n8n | Technology | stu-901 |
| Claude | Technology | vwx-234 |
| Manufacturing | Industry | yza-567 |
| System Integration | Industry | bcd-890 |

## Use Cases
| Name | Project | Status | Priority | Notion ID |
|------|---------|--------|----------|-----------|
| UC-1: Internal Handoffs | Document Extraction | Has Solutions | Critical | efg-123 |

## Issues
| Name | Type | Project | Status | Notion ID |
|------|------|---------|--------|-----------|
| Waiting for API credentials | Blocker | Document Extraction | Open | hij-456 |
```

### 3. Update Local Registry
If local entities exist that match Notion entities (by name/email), update them with Notion IDs.

### 4. Report Results
Output summary:
```
Notion sync completed:
  Companies: 12 fetched
  Contacts: 35 fetched
  Projects: 8 fetched
  Topics: 24 fetched
  Use Cases: 5 fetched
  Issues: 3 fetched

Matched to existing local entities: 15
  - Vioxx (client) → notion:abc-123
  - Brandon Smith (person) → notion:ghi-789
  ...

Cache saved: ./knowledge/notion-cache.md
```

## Using the Notion Plugin

To query Notion databases, use the existing Notion plugin:

```
# Example: Query Companies
Use /notion skill or mcp_notion_query_database with:
- database_id: "2d7e7406-6c7d-81bd-a74b-eeb28c4aadc9"
- filter: {"property": "Type", "select": {"equals": "Client"}}
```

## Notes

- Run this command before processing transcripts for best entity matching
- Re-run periodically to pick up new Notion entities
- Does NOT create entities in Notion (read-only)
- Local entities flagged as "new" can be manually added to Notion later
- Cache includes Notion page IDs for future two-way sync potential

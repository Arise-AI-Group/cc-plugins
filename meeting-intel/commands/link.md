---
name: link
description: Re-run entity resolution to merge duplicates and update cross-references
---

# Re-link Entities

Re-run entity resolution across all processed meetings to:
- Merge duplicate entities
- Update cross-references after Notion sync
- Fix broken links
- Consolidate aliases

## Usage

```
/meeting-intel:link
```

## When to Use

- After running `/meeting-intel:sync-notion` to link local entities to Notion
- After manually editing entity files
- When duplicates are suspected
- To refresh all cross-references

## Workflow

### 1. Load All Entities
Read all entity files from `./knowledge/entities/*/`:
- Build map of ID → entity
- Build map of name → entity
- Build map of alias → entity
- Build map of email → entity

### 2. Load Notion Cache
If `./knowledge/notion-cache.md` exists:
- Build map of Notion name → Notion ID
- Build map of Notion email → Notion ID

### 3. Find Duplicates
Identify potential duplicates:
- Same name (case-insensitive)
- Same email
- Alias matches another entity's name
- Notion cache match without local Notion ID

### 4. Merge Duplicates
For each duplicate set:
- Keep the entity with the most mentions
- Merge aliases from all duplicates
- Merge mentions from all duplicates
- Update Notion ID if available
- Delete duplicate files
- Update registry

### 5. Update Cross-References
For each entity:
- Verify all `[[Entity Name]]` links resolve
- Update meeting files with corrected links
- Fix any broken relative paths

### 6. Link to Notion
For entities matching Notion cache:
- Add `notion_id` to frontmatter if not present
- Note the link in entity file

### 7. Update Registry
Rewrite `./knowledge/registry.md` with:
- All current entities
- Updated aliases
- Notion IDs

### 8. Report Results

```
Entity linking completed:

Duplicates merged: 3
  - "John" + "John Smith" → John Smith (person-001)
  - "Acme" + "Acme Corp" → Acme Corp (client-001)
  - "Project A" + "Project Alpha" → Project Alpha (project-001)

Notion links added: 8
  - Vioxx → notion:abc-123
  - Brandon Smith → notion:ghi-789
  - Document Extraction → notion:mno-345
  ...

Broken links fixed: 2
  - meetings/2025-01-15-loom-123.md: [[Jon Smith]] → [[John Smith]]
  - entities/projects/vioxx-poc.md: [[Brandan]] → [[Brandon Smith]]

Registry updated: ./knowledge/registry.md
```

## Duplicate Detection Rules

### People
- Same full name (case-insensitive)
- Same email address
- First name only matches full name's first name (with same company context)

### Companies
- Same company name (case-insensitive)
- Common abbreviations (Inc, Corp, LLC stripped)
- "Acme" matches "Acme Corp"

### Projects
- Same project name (case-insensitive)
- Same client + similar name

### Topics
- Same topic name (case-insensitive)
- Plurals (API/APIs)

## Merge Strategy

When merging duplicates:

1. **Keep primary:** Entity with most mentions OR oldest created date
2. **Merge aliases:** Combine all names/aliases from duplicates
3. **Merge mentions:** Combine all meeting mentions
4. **Preserve metadata:** Keep most complete metadata (email, role, etc.)
5. **Update ID:** Keep primary's ID, add others as aliases in registry

## Example

Before:
```
entities/people/john.md (2 mentions)
entities/people/john-smith.md (5 mentions)
```

After merge:
```
entities/people/john-smith.md (7 mentions, aliases: ["John"])
```

## Notes

- Always backs up before merging (creates `.bak` files)
- Prompts for confirmation on ambiguous merges
- Logs all changes to `./knowledge/link-log.md`
- Safe to run multiple times (idempotent)

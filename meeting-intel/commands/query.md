---
name: query
description: Search the meeting knowledge base for entities, meetings, and content
arguments:
  - name: search
    description: Search term or query
    required: true
  - name: type
    description: "Filter by entity type: person, client, project, topic, idea, decision, action-item, use-case, issue, meeting"
    required: false
  - name: since
    description: Filter to entities/meetings since date (YYYY-MM-DD)
    required: false
  - name: status
    description: "Filter action items/issues by status: pending, completed, open, resolved"
    required: false
---

# Query Knowledge Base

Search the meeting intelligence knowledge base for entities, meetings, and extracted information.

## Usage

```
/meeting-intel:query "Vioxx"                        # Search all entities for "Vioxx"
/meeting-intel:query "John" --type=person           # Search only people
/meeting-intel:query "API" --type=action-item --status=pending  # Pending action items about API
/meeting-intel:query "roadmap" --since=2025-01-01   # Recent mentions of roadmap
```

## Search Behavior

### 1. Load Knowledge Base
Read from `./knowledge/`:
- `registry.md` for quick entity lookup
- Entity files in `entities/*/`
- Meeting records in `meetings/`

### 2. Search Matching
Search across:
- Entity names and aliases
- Entity content and descriptions
- Meeting titles and summaries
- Transcript content (if searching meetings)

### 3. Apply Filters
If `--type` specified, limit to that entity type:
- `person` → `entities/people/`
- `client` → `entities/clients/`
- `project` → `entities/projects/`
- `topic` → `entities/topics/`
- `idea` → `entities/ideas/`
- `decision` → `entities/decisions/`
- `action-item` → `entities/action-items/`
- `use-case` → `entities/use-cases/`
- `issue` → `entities/issues/`
- `meeting` → `meetings/`

If `--since` specified, filter by created/updated date.

If `--status` specified (for action-items, issues, use-cases), filter by status field.

### 4. Return Results
Format results showing:
- Entity/meeting name with link
- Type and key metadata
- Relevant context snippet
- Related entities

## Example Queries

### Find a person
```
/meeting-intel:query "Trent"
```
Returns:
```
Found 1 match:

## People
- **[[Trent Christopher]]** (entities/people/trent-christopher.md)
  Role: Founder at Arise Group
  Mentioned in: 3 meetings
  Related: Vioxx, Morningside, Claude
```

### Find pending action items
```
/meeting-intel:query "" --type=action-item --status=pending
```
Returns:
```
Found 5 pending action items:

1. **[[Action: Draft PRD]]** (entities/action-items/draft-prd.md)
   Assignee: [[Trent Christopher]]
   Due: 2025-01-20
   Project: [[Vioxx]]
   From: Team Standup (2025-01-15)

2. **[[Action: Review Architecture]]** (entities/action-items/review-architecture.md)
   Assignee: [[Josh]]
   Due: None
   Project: [[Vioxx]]
   From: Technical Review (2025-01-16)
...
```

### Find all mentions of a topic
```
/meeting-intel:query "Claude" --type=topic
```
Returns:
```
Found 1 topic:

## [[Claude]] (entities/topics/claude.md)
Category: Technology
Description: AI assistant and coding tool

### Mentioned In:
- Team Standup (2025-01-15) - "I use Claude for everything..."
- Technical Review (2025-01-16) - "Claude also gave me open questions..."

### Related:
- Projects: [[Vioxx]], [[Internal Tools]]
- People: [[Trent Christopher]] (uses), [[Josh]] (uses)
```

### Search meeting content
```
/meeting-intel:query "project scoping" --type=meeting
```
Returns:
```
Found 1 meeting:

## [[Streamlining Project Scoping]] (meetings/2026-01-15-loom-77f7eb86.md)
Date: 2026-01-15
Source: Loom
Participants: Trent Christopher

### Summary:
Walkthrough of workspace structure for client projects using Claude...

### Relevant Excerpts:
- "...how I structure my workspace for managing client projects..."
- "...scope this project for me. And what it did was pretty remarkable..."
```

## Output Format

Results are formatted as markdown with:
- Entity names as wiki links `[[Name]]`
- File paths for reference
- Key metadata inline
- Context snippets where relevant
- Related entity links

## Notes

- Empty search with filters returns all matching entities
- Search is case-insensitive
- Partial name matches are included
- Related entities shown for context
- Meeting mentions include date and excerpt

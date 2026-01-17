---
name: meeting-intel
description: This skill should be used when the user asks to "process meeting transcript", "extract entities from meeting", "build knowledge graph", "find action items across meetings", "query meeting knowledge", "sync Notion entities", "who was mentioned in meetings", "what decisions were made". Provides meeting intelligence by extracting entities, decisions, action items, and building interconnected markdown knowledge bases from Fireflies, Loom, and Fathom transcripts.
---

# Meeting Intelligence

Extract structured knowledge from meeting transcripts. Build an interconnected markdown knowledge base with people, companies, projects, topics, decisions, action items, use cases, and issues.

## Overview

This skill processes meeting transcripts from:
- **Fireflies** (`./transcripts/fireflies/`)
- **Loom** (`./transcripts/loom/`)
- **Fathom** (`./transcripts/fathom/`)

And creates a knowledge graph in:
- **Knowledge Base** (`./knowledge/`)

## Storage Structure

```
./knowledge/
├── entities/
│   ├── people/           # Person profiles
│   ├── clients/          # Company/client profiles
│   ├── projects/         # Project details
│   ├── topics/           # Topic summaries
│   ├── ideas/            # Ideas from meetings
│   ├── decisions/        # Decisions made
│   ├── action-items/     # Action items with status
│   ├── use-cases/        # Requirements discovered
│   └── issues/           # Blockers, questions, risks
├── meetings/             # Processed meeting records
├── registry.md           # Entity registry with IDs and aliases
└── notion-cache.md       # Cached Notion entities (optional)
```

## Entity Extraction

When processing a meeting transcript, extract the following entities:

### 1. People
Extract all mentioned people with:
- **Full name** (best effort from context)
- **Role/title** if mentioned
- **Company affiliation** if mentioned
- **Email** if mentioned
- **Aliases** used in the meeting (nicknames, first names only)

**File format:** `entities/people/{name-slug}.md`
```markdown
---
id: person-{unique-id}
name: Full Name
aliases: ["Nickname", "First Name"]
email: email@example.com
company: Company Name
role: Job Title
notion_id:  # If linked to Notion
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Full Name

**Role:** {Role} at {Company}
**First seen:** {Meeting Title} ({Date})

## Mentions
- [{Meeting Title}](../meetings/{meeting-file}.md) - Context of mention

## Related
- Projects: [[Project Name]]
- Topics: [[Topic Name]]
```

### 2. Companies/Clients
Extract organizations mentioned:
- **Company name**
- **Industry/type** if mentioned
- **Relationship** (client, vendor, partner, internal)
- **Website** if mentioned

**File format:** `entities/clients/{company-slug}.md`
```markdown
---
id: client-{unique-id}
name: Company Name
type: Client|Vendor|Partner|Internal
industry: Industry
website: https://example.com
notion_id:  # If linked to Notion
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Company Name

**Type:** {Type}
**Industry:** {Industry}

## Contacts
- [[Person Name]] - {Role}

## Projects
- [[Project Name]]

## Mentions
- [{Meeting Title}](../meetings/{meeting-file}.md) - Context
```

### 3. Projects
Extract project references:
- **Project name**
- **Client/company** association
- **Status** if mentioned
- **Key contacts**

**File format:** `entities/projects/{project-slug}.md`
```markdown
---
id: project-{unique-id}
name: Project Name
client: Company Name
status: Active|Completed|On Hold
notion_id:
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Project Name

**Client:** [[Company Name]]
**Status:** {Status}

## Key Contacts
- [[Person Name]] - {Role}

## Topics
- [[Topic Name]]

## Mentions
- [{Meeting Title}](../meetings/{meeting-file}.md) - Context
```

### 4. Topics
Extract key subjects/technologies discussed:
- **Topic name**
- **Category** (Technology, Industry, Process, Skill, Concept)
- **Brief description**

**File format:** `entities/topics/{topic-slug}.md`
```markdown
---
id: topic-{unique-id}
name: Topic Name
category: Technology|Industry|Process|Skill|Concept
notion_id:
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Topic Name

**Category:** {Category}

## Description
Brief description of the topic.

## Related
- Projects: [[Project Name]]
- People: [[Person Name]] (expertise)

## Mentions
- [{Meeting Title}](../meetings/{meeting-file}.md) - Context
```

### 5. Ideas
Extract new ideas or suggestions:
- **Idea summary**
- **Proposer** (who suggested it)
- **Related project/topic**

**File format:** `entities/ideas/{idea-slug}.md`
```markdown
---
id: idea-{unique-id}
summary: Brief summary
proposer: Person Name
project: Project Name
topic: Topic Name
source_meeting: meeting-file.md
notion_id:
created: YYYY-MM-DD
---

# {Brief Summary}

**Proposed by:** [[Person Name]]
**Meeting:** [{Meeting Title}](../meetings/{meeting-file}.md)
**Date:** {Date}

## Description
Full description of the idea.

## Related
- Project: [[Project Name]]
- Topic: [[Topic Name]]
```

### 6. Decisions
Capture decisions made:
- **Decision statement**
- **Who made it**
- **Rationale** if provided
- **Related project**

**File format:** `entities/decisions/{decision-slug}.md`
```markdown
---
id: decision-{unique-id}
decision: Decision statement
made_by: Person Name
project: Project Name
source_meeting: meeting-file.md
notion_id:
created: YYYY-MM-DD
---

# Decision: {Brief Title}

**Made by:** [[Person Name]]
**Meeting:** [{Meeting Title}](../meetings/{meeting-file}.md)
**Date:** {Date}

## Decision
{Full decision statement}

## Rationale
{Why this decision was made}

## Related
- Project: [[Project Name]]
- Topic: [[Topic Name]]
```

### 7. Action Items
Extract tasks assigned:
- **Task description**
- **Assignee**
- **Due date** if mentioned
- **Status** (pending/completed)

**File format:** `entities/action-items/{action-slug}.md`
```markdown
---
id: action-{unique-id}
task: Task description
assignee: Person Name
due_date: YYYY-MM-DD
status: pending|completed
project: Project Name
source_meeting: meeting-file.md
notion_id:
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Action: {Brief Title}

**Assignee:** [[Person Name]]
**Due:** {Due Date}
**Status:** {Status}
**Meeting:** [{Meeting Title}](../meetings/{meeting-file}.md)

## Task
{Full task description}

## Related
- Project: [[Project Name]]
```

### 8. Use Cases
Extract requirements or needs discovered:
- **Name** (UC-X: descriptive title)
- **Related project**
- **Priority** (Critical/High/Medium/Low)
- **Impact** if mentioned

**File format:** `entities/use-cases/{use-case-slug}.md`
```markdown
---
id: use-case-{unique-id}
name: UC-X: Descriptive Title
project: Project Name
priority: Critical|High|Medium|Low
status: Open|Investigating|Has Solutions|Resolved
source_meeting: meeting-file.md
notion_id:
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# UC-X: Descriptive Title

**Project:** [[Project Name]]
**Priority:** {Priority}
**Status:** {Status}
**Discovered:** [{Meeting Title}](../meetings/{meeting-file}.md)

## Description
{Full description of the use case/requirement}

## Impact
{Why this matters}
```

### 9. Issues
Extract blockers, questions, risks:
- **Type** (Blocker, Question, Risk, Decision)
- **Description**
- **Owner** (Arise or Client)
- **Related project**

**File format:** `entities/issues/{issue-slug}.md`
```markdown
---
id: issue-{unique-id}
name: Issue description
type: Blocker|Question|Risk|Decision
owner: Arise|Client
project: Project Name
status: Open|In Progress|Resolved
source_meeting: meeting-file.md
notion_id:
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# {Issue Type}: {Brief Title}

**Type:** {Type}
**Owner:** {Owner}
**Project:** [[Project Name]]
**Status:** {Status}
**Raised:** [{Meeting Title}](../meetings/{meeting-file}.md)

## Description
{Full description}

## Resolution
{If resolved, how it was resolved}
```

## Meeting Record Format

After processing a transcript, create a meeting record:

**File format:** `meetings/{date}-{source}-{id}.md`
```markdown
---
id: meeting-{date}-{source}-{id}
source: fireflies|loom|fathom
source_id: original-id
title: Meeting Title
date: YYYY-MM-DD
participants: ["person-id-1", "person-id-2"]
processed: YYYY-MM-DDTHH:MM:SSZ
---

# {Meeting Title}

**Date:** {Date}
**Source:** {Source}
**Participants:** [[Person 1]], [[Person 2]]

## Summary
{AI-generated summary of the meeting}

## Extracted Entities

### People
- [[Person Name]] - {Role/context}

### Companies
- [[Company Name]] - {Relationship}

### Projects
- [[Project Name]] - {Context}

### Topics Discussed
- [[Topic Name]] - {Brief context}

### Decisions Made
- [[Decision: Brief Title]] - {Summary}

### Action Items
- [ ] [[Action: Brief Title]] - {Assignee}

### Ideas
- [[Idea: Brief Title]] - {Proposer}

### Use Cases
- [[UC-X: Title]] - {Priority}

### Issues
- [[Issue: Title]] - {Type}

## Full Transcript
{Original transcript content - preserved for reference}
```

## Registry Format

Maintain a registry of all entities for resolution:

**File:** `registry.md`
```markdown
---
updated: YYYY-MM-DDTHH:MM:SSZ
---

# Entity Registry

## People
| ID | Name | Aliases | Email | Notion ID |
|----|------|---------|-------|-----------|
| person-001 | John Smith | John, JS | john@example.com | abc123 |

## Companies
| ID | Name | Type | Notion ID |
|----|------|------|-----------|
| client-001 | Acme Corp | Client | def456 |

## Projects
| ID | Name | Client | Notion ID |
|----|------|--------|-----------|
| project-001 | Project Alpha | Acme Corp | ghi789 |

## Topics
| ID | Name | Category | Notion ID |
|----|------|----------|-----------|
| topic-001 | Claude | Technology | jkl012 |
```

## Entity Resolution

When extracting entities, follow this resolution logic:

1. **Check registry first:**
   - Exact name match → Link to existing entity
   - Alias match → Link to existing entity
   - Email match → Link to existing entity

2. **Check Notion cache (if available):**
   - Match against cached Notion entities
   - If match found, note the Notion ID

3. **Fuzzy matching:**
   - First + last name combination
   - Company name variations
   - Add as alias if high confidence match

4. **Create new entity:**
   - If no match found, create new entity file
   - Add to registry

5. **Always update:**
   - Add meeting to entity's "Mentions" section
   - Update registry if aliases discovered

## Notion Integration

When Notion cache is available (`./knowledge/notion-cache.md`), prioritize matching against existing Notion entities:

### Notion Database IDs (Data Source IDs)
Use these IDs when querying via the Notion plugin:
- **Companies:** `2d7e7406-6c7d-8179-9155-000bd8622964`
- **Contacts:** `2d5e7406-6c7d-818c-bc3d-000b38dab7e4`
- **Projects:** `2d5e7406-6c7d-8167-bb16-000b3ec34789`
- **Topics:** `2d6e7406-6c7d-8172-a05d-000b640837df`
- **Notes:** `2d6e7406-6c7d-810b-97b2-000b1fdedb1e`
- **Use Cases:** `089cfc11-6c4b-45e6-a1e1-805178e2e732`
- **Issues:** `b376fcbe-cdd0-4c95-b9e9-c07e098baec7`

### Matching Priority
1. Notion entity (by name/email) → Link with Notion ID
2. Local registry → Link to existing
3. Create new (flag as candidate for Notion)

## Commands

- `/meeting-intel:process [path]` - Process transcripts and extract entities
- `/meeting-intel:query <search>` - Search the knowledge base
- `/meeting-intel:sync-notion` - Fetch entities from Notion
- `/meeting-intel:link` - Re-run entity resolution

## Workflow

1. **Ingest:** User fetches transcripts using Fireflies/Loom/Fathom plugins
2. **Process:** Run `/meeting-intel:process` to extract entities
3. **Enrich:** Optionally run `/meeting-intel:sync-notion` to match Notion entities
4. **Query:** Use `/meeting-intel:query` to search knowledge base
5. **Link:** Run `/meeting-intel:link` after adding new Notion cache

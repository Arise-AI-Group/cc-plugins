---
name: process
description: Process meeting transcripts and extract entities into the knowledge base
arguments:
  - name: path
    description: Optional path to specific transcript file. If omitted, processes all unprocessed transcripts in ./transcripts/
    required: false
---

# Process Meeting Transcripts

Process meeting transcripts from Fireflies, Loom, or Fathom and extract entities into the knowledge base.

## Usage

```
/meeting-intel:process                    # Process all unprocessed transcripts
/meeting-intel:process ./transcripts/loom/meeting.md  # Process specific file
```

## Workflow

### 1. Setup Knowledge Directory
First, ensure the knowledge directory structure exists:

```bash
mkdir -p ./knowledge/entities/people
mkdir -p ./knowledge/entities/clients
mkdir -p ./knowledge/entities/projects
mkdir -p ./knowledge/entities/topics
mkdir -p ./knowledge/entities/ideas
mkdir -p ./knowledge/entities/decisions
mkdir -p ./knowledge/entities/action-items
mkdir -p ./knowledge/entities/use-cases
mkdir -p ./knowledge/entities/issues
mkdir -p ./knowledge/meetings
```

### 2. Load Registry
Read `./knowledge/registry.md` if it exists to get current entity mappings.

### 3. Load Notion Cache (Optional)
If `./knowledge/notion-cache.md` exists, load it for entity matching priority.

### 4. Find Transcripts to Process
If no path specified, scan these directories for .md files:
- `./transcripts/fireflies/`
- `./transcripts/loom/`
- `./transcripts/fathom/`

Check each file against `./knowledge/meetings/` to see if already processed.

### 5. For Each Transcript

#### 5.1 Read and Parse
Read the transcript file and extract:
- **Title** from the first `# ` heading
- **Date** from metadata or filename
- **Source** from directory (fireflies/loom/fathom)
- **Source ID** from filename or metadata
- **Participants** from metadata if available
- **Full transcript content**

#### 5.2 Extract Entities
Using the entity extraction prompts from the skill, identify:

**People:**
- Look for names mentioned (speakers, references)
- Extract role/company if context provides
- Note any aliases or nicknames used

**Companies:**
- Client names mentioned
- Vendor or partner organizations
- Industry context if mentioned

**Projects:**
- Project names or codenames
- Client association
- Status updates

**Topics:**
- Technologies discussed (Claude, n8n, Python, etc.)
- Industry terms
- Process or methodology mentions

**Ideas:**
- New suggestions or proposals
- Who proposed them
- Related context

**Decisions:**
- Explicit decisions made
- Who made the decision
- Rationale if provided

**Action Items:**
- Tasks assigned with "will do", "need to", "action item"
- Assignee identification
- Due dates if mentioned

**Use Cases:**
- Requirements or needs discovered
- Priority indicators
- Impact statements

**Issues:**
- Blockers mentioned
- Questions raised
- Risks identified
- Key decisions (distinct from Ideas)

#### 5.3 Resolve Entities
For each extracted entity:

1. Check registry for existing match (name, alias, email)
2. Check Notion cache for match
3. If match found: link to existing entity, add this meeting to mentions
4. If no match: create new entity file, add to registry

#### 5.4 Create/Update Entity Files
Write or update entity markdown files with:
- YAML frontmatter with metadata
- Content sections
- Meeting mention added

#### 5.5 Create Meeting Record
Write meeting file to `./knowledge/meetings/{date}-{source}-{id}.md` with:
- Full metadata
- Summary (generate from transcript)
- All extracted entities linked
- Full transcript preserved

#### 5.6 Update Registry
Add any new entities to `./knowledge/registry.md`

### 6. Report Results
Output summary of processing:
- Number of transcripts processed
- Entities extracted (by type)
- New entities created
- Existing entities updated
- Any unresolved references (flag for review)

## Example Output

```
Processed 1 transcript:
  ./transcripts/loom/streamlining-project-scoping-77f7eb86.md

Extracted Entities:
  People: 3 (2 new, 1 matched)
    - Trent Christopher (new)
    - Josh (new)
    - Nick (new)

  Companies: 2 (2 new)
    - Vioxx (new)
    - Morningside (new)

  Topics: 4 (4 new)
    - Claude (new)
    - Jira (new)
    - Sticky Notes (new)
    - Whisperflow (new)

  Ideas: 2
  Decisions: 1
  Action Items: 3

Meeting record created:
  ./knowledge/meetings/2026-01-15-loom-77f7eb86.md

Registry updated: ./knowledge/registry.md
```

## Notes

- Always preserve the original transcript in the meeting record
- Use wiki-style links `[[Entity Name]]` for cross-references
- Slugify entity names for filenames (lowercase, hyphens)
- Include source meeting in all entity mentions
- Flag ambiguous entities for human review

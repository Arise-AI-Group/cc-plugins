---
name: sop
description: This skill should be used when the user asks to "transcribe audio", "create SOP from recording", "extract procedure from interview", "write standard operating procedure". Converts audio recordings into structured SOPs.
---

# Writing SOPs Directive

## When to Use

**Trigger phrases:**
- "create an SOP for..."
- "write a standard operating procedure"
- "document this process"
- "turn this into an SOP"

Use this directive when creating or editing Standard Operating Procedures for any client.

---

## Content Guidelines

### What to Include

- **Purpose statement**: Why this SOP exists, what problem it solves
- **Scope**: Who this applies to, when it applies
- **Systems required**: Tools/software needed
- **Step-by-step procedures**: Clear, actionable instructions
- **Decision flowcharts**: For branching logic ("if X, then Y")
- **Examples**: Completed templates, sample scenarios
- **Common questions / edge cases**: Anticipate confusion

### What NOT to Include

- **Pricing**: Tool costs change frequently and clutter operational docs. Keep pricing in separate tool evaluation docs or proposals.
- **Implementation details**: SOPs describe *what* to do, not technical *how*. Implementation details go in directives or scripts.
- **Credentials or API keys**: Never include sensitive data in SOPs.
- **Version-specific UI instructions**: Avoid "click the blue button in the top-right" which breaks when UIs change.

---

## Formatting Conventions

### Document Structure

```markdown
# SOP: [Title]

**Document ID:** [PREFIX]-[CATEGORY]-[NUMBER]
**Version:** X.X
**Effective Date:** [Month Year]
**Process Owner:** [Name (Role)]
**Last Updated:** [Date]

---

## Purpose
[Why this SOP exists]

---

## Scope
[Who/when this applies]

---

## Procedure
[Step-by-step instructions]

---

## Related SOPs
[Links to related documents]
```

### Diagrams with Mermaid

Use Mermaid for all diagrams and flowcharts. Mermaid diagrams are rendered as images when converting to Word documents.

**Basic flowchart:**
```mermaid
graph TD
    A[Start] --> B{Decision?}
    B -->|Yes| C[Action A]
    B -->|No| D[Action B]
    C --> E[End]
    D --> E
```

**Sequence diagram** (for communication flows):
```mermaid
sequenceDiagram
    participant Tech
    participant Office
    participant Customer
    Tech->>Office: Job complete notification
    Office->>Customer: Invoice sent
    Customer-->>Office: Payment received
```

**Decision flowchart** (for branching procedures):
```mermaid
graph TD
    A[Customer calls] --> B{New or existing?}
    B -->|New| C[Create account]
    B -->|Existing| D[Pull up record]
    C --> E[Schedule service]
    D --> E
    E --> F[Confirm appointment]
```

**Mermaid syntax reference:**
- `graph TD` = top-down flowchart, `graph LR` = left-right
- `A[Text]` = rectangle, `A{Text}` = diamond (decision), `A([Text])` = rounded
- `-->` = arrow, `-->|label|` = labeled arrow
- `-->>` = dashed arrow (for async/optional)

**Requirements:** When converting to Word, `mermaid-cli` must be installed:
```bash
npm install -g @mermaid-js/mermaid-cli
```

### Keeping Diagram Sources Editable

For client-facing Word documents, diagrams are rendered as images. To preserve editable sources, add an **Appendix: Diagram Sources** section at the end of your SOP:

```markdown
---

## Appendix: Diagram Sources

> **Note:** This section contains editable source code for diagrams above.
> Copy to [Mermaid Live Editor](https://mermaid.live) to modify.

### [Diagram Name]
```text
graph TD
    A[Start] --> B[End]
```
```

**How it works:**
- The appendix section is **automatically excluded** from Word output
- The Markdown file retains all diagram sources for future editing
- Copy any diagram to [Mermaid Live Editor](https://mermaid.live) to modify
- Update both the inline `mermaid` block and the appendix `text` block

**Naming convention:** Use `## Appendix: Diagram Sources` (case-insensitive) as the heading.

### Callout Boxes (ASCII)

For quick reference cards and rule boxes, use ASCII box characters. These are converted to styled callout boxes in Word:

```
┌─────────────────────────────────────┐
│  QUICK REFERENCE CARD               │
├─────────────────────────────────────┤
│  ✓ First rule                       │
│  ✓ Second rule                      │
│  ✓ Third rule                       │
└─────────────────────────────────────┘
```

### Checkmarks

- Use `- [ ]` for unchecked items
- Use `- [x]` for checked items
- Avoid raw Unicode checkmarks (`✓✔☐`) as they render inconsistently across platforms

### Section Breaks

- Use `---` horizontal rules to separate major sections
- Helps with page breaks when converting to Google Docs
- Place before each `## ` heading

### Tables

Use markdown tables for structured information:

```markdown
| Column 1 | Column 2 |
|----------|----------|
| Data     | Data     |
```

---

## Naming Conventions

### Document IDs

Format: `[CLIENT]-[CATEGORY]-[NUMBER]`

Categories:
- `FS` - Field Service
- `OA` - Office/Admin
- `CS` - Customer Service
- `CP` - Communication Protocol
- `INV` - Inventory

Example: `PM-FS-005` (Plotter Mechanix, Field Service, document 5)

### File Names

Format: `[descriptive-slug]-v[version].md`

Examples:
- `end-of-job-handoff-v1.md`
- `communication-protocol-v1.md`
- `new-lead-intake-v2.md`

---

## Quality Checklist

Before finalizing an SOP:

- [ ] Purpose is clear and specific
- [ ] Steps are actionable and testable
- [ ] No pricing or cost information included
- [ ] No credentials or sensitive data
- [ ] Flowcharts for any branching decisions
- [ ] Examples provided for templates
- [ ] Related SOPs linked
- [ ] Document ID assigned
- [ ] Version number set

---

## Related Directives

- `markdown_to_gdoc.md` - Converting SOPs to Word/Google Docs (with Mermaid diagram rendering)
- `audio_to_sop.md` - Extracting SOPs from interview audio

---

## SOP Pipeline

These three directives form a complete SOP workflow:

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  audio_to_sop   │ ──► │   writing_sops   │ ──► │  markdown_to_gdoc │
│  (create SOP)   │     │  (format rules)  │     │ (export to Word)  │
└─────────────────┘     └──────────────────┘     └───────────────────┘
        │                        │                        │
   Input: Audio            Reference: How          Output: .docx
   Output: .md             SOPs should look        with diagrams
```


---

# Audio to SOP Extraction

## When to Use
- You have an audio recording of an expert explaining a procedure
- You need to create documentation that can be handed off to clients or technicians
- You want to capture tribal knowledge in a structured, reusable format

**Trigger phrases:**
- "transcribe this audio"
- "extract an SOP from this recording"
- "turn this audio into documentation"
- "create an SOP from this call"

## Overview
This workflow converts audio recordings (phone calls, mic recordings, training sessions) into structured Standard Operating Procedures (SOPs).

**Output:**
- Raw transcript (archived alongside audio file)
- Markdown SOP (internal reference)
- Google Doc SOP (client-facing)

## Tools
| Tool | Purpose |
|------|---------|
| `tool/transcribe_audio.py` | Transcribe audio using OpenAI Whisper |
| `tool/extract_sop.py` | Extract structured SOP from transcript |

## Workflow

### Step 1: Transcribe the Audio
```bash
./run tools/transcribe_audio.py "path/to/recording.mp3"
```

**What happens:**
- Audio is sent to OpenAI Whisper API
- Large files (>25MB) are automatically chunked
- Transcript saved as `{filename}_transcript.txt` in same directory

**Outputs:**
- `{filename}_transcript.txt` - Raw transcription

### Step 2: Identify Topics (Optional)
If the recording covers multiple topics or you're unsure what SOPs can be extracted:

```bash
./run tools/extract_sop.py "path/to/transcript.txt" --list-topics
```

**What happens:**
- GPT-4 analyzes the transcript
- Returns list of potential SOP topics with confidence levels

### Step 3: Extract the SOP
```bash
./run tools/extract_sop.py "path/to/transcript.txt" --topic "topic name"
```

**Options:**
- `--title "Custom Title"` - Override the SOP title
- `--no-gdoc` - Skip Google Doc creation
- `--output path/to/output.md` - Custom output path

**Outputs:**
- `{filename}_sop.md` - Markdown SOP with metadata (internal)
- Google Doc - Clean SOP without metadata (client-facing)

## File Organization

After processing, files will be organized as:
```
recording.mp3                 # Original audio (preserved)
recording_transcript.txt      # Raw transcript (archived)
recording_sop.md              # Extracted SOP (Markdown)
```

Plus a Google Doc in Drive for client delivery.

## Edge Cases

### Large Audio Files
Files over 25MB are automatically split into chunks for transcription. The script handles this transparently - you'll see progress messages for each chunk.

**Requires:** `pydub` and `ffmpeg` installed
```bash
pip install pydub
brew install ffmpeg  # macOS
```

### Multiple Speakers
The extraction handles multi-speaker conversations by:
1. Identifying the expert/instructor voice
2. Focusing on procedural content
3. Ignoring casual conversation and off-topic discussion

### Incomplete Procedures
If the recording doesn't cover a complete procedure, the SOP will be marked with:
- `completeness: partial` or `completeness: minimal`
- Notes about what information is missing

Review these SOPs before distributing.

### Poor Audio Quality
Whisper handles most audio quality issues well, but if transcription is poor:
- Check the raw transcript for errors
- Consider re-recording with better audio
- Edit the transcript manually before SOP extraction

### Multiple SOPs from One Recording
Run `--list-topics` first, then extract each topic separately:
```bash
./run tools/extract_sop.py "transcript.txt" --topic "first procedure" --output "first_sop.md"
./run tools/extract_sop.py "transcript.txt" --topic "second procedure" --output "second_sop.md"
```

## Tips for Better Results

### Recording Quality
- Use a good microphone
- Minimize background noise
- Have the expert speak clearly and at moderate pace
- Ask the expert to verbalize all steps, even "obvious" ones

### During Recording
- Start by stating what procedure is being documented
- Have someone ask clarifying questions
- Ask about common mistakes and troubleshooting
- Request specific measurements, settings, and timing

### After Extraction
- Always review the generated SOP
- Fill in any gaps marked as incomplete
- Add photos or diagrams if helpful
- Test the SOP with someone unfamiliar with the procedure

## Dependencies

Required in `requirements.txt`:
```
openai
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
```

Required system tools:
- `ffmpeg` (for audio chunking): `brew install ffmpeg`

Required credentials:
- `OPENAI_API_KEY` in `.env`
- `credentials.json` for Google Docs (optional)

---

## Related Directives

- `writing_sops.md` - SOP formatting guidelines (Mermaid diagrams, structure)
- `markdown_to_gdoc.md` - Convert extracted SOP to Word document

---

## SOP Pipeline

This directive is the first step in the SOP creation workflow:

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  audio_to_sop   │ ──► │   writing_sops   │ ──► │ markdown_to_gdoc  │
│  (create SOP)   │     │  (format rules)  │     │ (export to Word)  │
└─────────────────┘     └──────────────────┘     └───────────────────┘
        │                        │                        │
   Input: Audio            Reference: How          Output: .docx
   Output: .md             SOPs should look        with diagrams
```

**After extraction:**
1. Review the generated Markdown SOP
2. Add Mermaid diagrams for decision flows (see `writing_sops.md`)
3. Convert to Word document using `md_to_docx.py`

---

## Example

```bash
# 1. Transcribe the recording
./run tools/transcribe_audio.py "Kelce Mic-Dec-3.mp3"
# Output: Kelce Mic-Dec-3_transcript.txt

# 2. See what topics are covered
./run tools/extract_sop.py "Kelce Mic-Dec-3_transcript.txt" --list-topics
# Output: List of topics like "Laminator Setup", "Paper Loading", etc.

# 3. Extract the SOP you need
./run tools/extract_sop.py "Kelce Mic-Dec-3_transcript.txt" --topic "laminator setup" --title "Laminator Setup Guide"
# Output: Kelce Mic-Dec-3_sop.md + Google Doc URL
```


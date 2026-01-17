---
name: loom
description: This skill should be used when the user asks to "get loom transcript", "extract loom video text", "get comments from loom", "transcribe loom video", "what was said in the loom". Provides access to transcripts and comments from public Loom videos.
---

# Loom Video Transcription

## Purpose

Extract transcripts and comments from public Loom videos. Use this for getting video content as text, extracting action items from recordings, or reviewing video comments.

## Saving Transcripts

When extracting transcripts, **always save them to a file** in the user's working directory (not cache):

### Default Location

Save transcripts to `./transcripts/loom/` in the current working directory:

```
./transcripts/loom/
  {video-title}-{video-id}.md
```

### File Naming Convention

- Use the video title (sanitized for filesystem)
- Include the video ID for uniqueness
- Use `.md` format for readability

Example: `./transcripts/loom/project-kickoff-abc123def456.md`

### Transcript File Format

```markdown
# {Video Title}

**By:** {Creator Name}
**Date:** {Created Date}
**Video:** https://www.loom.com/share/{VIDEO_ID}

---

## Transcript

[00:00] Speaker: First sentence...
[00:15] Speaker: Next sentence...
```

### Workflow

1. Fetch the transcript using CLI or MCP
2. Create the output directory if needed: `mkdir -p ./transcripts/loom`
3. Write the formatted transcript to file
4. Report the saved file path to the user

## Trigger Phrases

- "Get the transcript from this Loom"
- "What was said in the Loom video?"
- "Extract text from Loom recording"
- "Get comments from the Loom"
- "Transcribe this Loom video"
- "Summarize this Loom" (get transcript first, then summarize)

## Execution Methods

### Primary: MCP Tools

The plugin provides MCP tools that work directly in Claude Code:
- `loom_get_transcript` - Get transcript from a video
- `loom_get_comments` - Get comments from a video

### Fallback: Python CLI

Use when MCP tools are unavailable:

**Location:** `tool/loom_api.py`

---

## Core Operations

### Get Transcript

```bash
# Get transcript as JSON
./run tool/loom_api.py transcript https://www.loom.com/share/VIDEO_ID

# Get transcript as readable text
./run tool/loom_api.py transcript https://www.loom.com/share/VIDEO_ID --output-format text

# Using just the video ID
./run tool/loom_api.py transcript VIDEO_ID -o text
```

**Output includes:**
- Video title and creator
- Speaker-identified sentences
- Timestamps for each segment

### Get Comments

```bash
# Get comments as JSON
./run tool/loom_api.py comments https://www.loom.com/share/VIDEO_ID

# Get comments as readable text
./run tool/loom_api.py comments VIDEO_ID --output-format text
```

**Output includes:**
- Comment author and text
- Video timestamp where comment was made
- Threaded replies

---

## URL Formats

Supported Loom URL formats:
- `https://www.loom.com/share/abc123def456`
- `https://loom.com/share/abc123def456`
- `https://www.loom.com/embed/abc123def456`
- Just the video ID: `abc123def456`

---

## Common Workflows

### Summarize a Loom Video

```bash
# 1. Get the transcript
./run tool/loom_api.py transcript https://www.loom.com/share/abc123 -o text
# 2. Share output with Claude for summarization
```

### Extract Action Items

1. Get transcript using CLI or MCP tool
2. Ask Claude to identify action items, decisions, and next steps

### Review Video Feedback

```bash
# Get all comments to see viewer questions/feedback
./run tool/loom_api.py comments VIDEO_ID -o text
```

---

## Requirements

- Works with **public Loom videos only**
- No API key required
- Node.js required for MCP server

---

## Limitations

- Only works with public/shared Loom videos
- Private workspace videos require Loom authentication (not supported)
- Transcript quality depends on Loom's automatic transcription

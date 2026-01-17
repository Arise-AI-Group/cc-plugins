---
name: loom
description: This skill should be used when the user asks to "get loom transcript", "extract loom video text", "get comments from loom", "transcribe loom video", "what was said in the loom". Provides access to transcripts and comments from public Loom videos.
---

# Loom Video Transcription

## Purpose

Extract transcripts and comments from public Loom videos. Use this for getting video content as text, extracting action items from recordings, or reviewing video comments.

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

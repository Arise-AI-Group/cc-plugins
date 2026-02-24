---
name: youtube
description: This skill should be used when the user asks to "get youtube transcript", "extract youtube video text", "transcribe youtube video", "what was said in the youtube video", "get captions from youtube", "list youtube transcript languages". Retrieves transcripts and available languages from public YouTube videos without an API key.
---

# YouTube Video Transcription

## Purpose

Extract transcripts from public YouTube videos. Use for getting video content as text, summarizing recordings, extracting action items, or reviewing educational content. No YouTube API key required.

## Saving Transcripts

When extracting transcripts, **always save them to a file** in the user's working directory.

### Default Location

Save to `./transcripts/youtube/` in the current working directory:

```
./transcripts/youtube/{video-id}.md
```

### Transcript File Format

```markdown
# YouTube Transcript

**Video:** https://www.youtube.com/watch?v={VIDEO_ID}
**Language:** {Language} ({code})
**Type:** Auto-generated | Manual

---

[00:00] First sentence of transcript...
[00:15] Next sentence of transcript...
```

### Workflow

1. Fetch the transcript using MCP tool or CLI
2. Create the output directory if needed: `mkdir -p ./transcripts/youtube`
3. Write the formatted transcript to file
4. Report the saved file path to the user

## Trigger Phrases

- "Get the transcript from this YouTube video"
- "What was said in the YouTube video?"
- "Extract text from YouTube"
- "Transcribe this YouTube video"
- "Get captions from YouTube"
- "What languages are available for this video?"
- "Summarize this YouTube video" (get transcript first, then summarize)

## Execution Methods

### Primary: MCP Tools

The plugin provides MCP tools that work directly in Claude Code:
- `youtube_get_transcript` - Get transcript text from a video
- `youtube_list_languages` - List available transcript languages

### Fallback: Python CLI

Use when MCP tools are unavailable.

**Location:** `tool/youtube_api.py`

## Core Operations

### Get Transcript

```bash
# JSON output (default: English)
./run tool/youtube_api.py transcript https://www.youtube.com/watch?v=VIDEO_ID

# Readable text with timestamps
./run tool/youtube_api.py transcript VIDEO_ID -o text

# Specific language
./run tool/youtube_api.py transcript VIDEO_ID --lang de -o text
```

### List Available Languages

```bash
./run tool/youtube_api.py languages VIDEO_ID -o text
```

## URL Formats

Supported YouTube URL formats:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- Bare video ID: `dQw4w9WgXcQ`

## Common Workflows

### Summarize a YouTube Video
1. Get transcript via MCP tool or CLI
2. Summarize the content

### Extract Key Points
1. Get transcript
2. Identify key points, action items, or main topics

### Multi-Language
1. Check available languages: `youtube_list_languages`
2. Fetch in desired language: `youtube_get_transcript` with `lang` parameter

## Requirements

- Public YouTube videos with captions (manual or auto-generated)
- No API key required
- Python 3.8+

## Limitations

- Only works with videos that have captions
- Private or age-restricted videos may not work
- Auto-generated transcript quality depends on YouTube's captioning

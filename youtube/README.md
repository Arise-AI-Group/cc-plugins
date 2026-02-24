# YouTube Plugin

Get transcripts from public YouTube videos. No API key required.

## Features

- Extract full transcripts with timestamps
- List available transcript languages
- Language selection with automatic fallback
- Multiple YouTube URL formats supported

## Installation

```bash
./setup.sh
```

## Usage

### MCP Tools (Primary)

- `youtube_get_transcript` - Get transcript from a YouTube video
- `youtube_list_languages` - List available transcript languages

### CLI (Fallback)

```bash
# Get transcript
./run tool/youtube_api.py transcript https://www.youtube.com/watch?v=VIDEO_ID
./run tool/youtube_api.py transcript VIDEO_ID -o text --lang en

# List available languages
./run tool/youtube_api.py languages VIDEO_ID -o text
```

## Output Formats

- `json` (default): Structured data with metadata
- `text`: Human-readable markdown with timestamps

## URL Formats

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`
- Bare video ID: `VIDEO_ID`

## Requirements

- Python 3.8+
- Public YouTube video with captions
- No API key required

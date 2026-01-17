# Loom Plugin

Get transcripts and comments from public Loom videos.

## Features

- Extract full transcripts with speaker identification and timestamps
- Get all comments and replies from videos
- Works with public Loom videos - no API key required

## Installation

```bash
./setup.sh
```

Or install as a Claude Code plugin:
```bash
/plugin install loom@cc-plugins
```

## Usage

### MCP Server (Primary)

The plugin includes an MCP server that provides tools directly to Claude Code:
- `get_transcript` - Get transcript from a Loom video
- `get_comments` - Get comments from a Loom video

### CLI (Fallback)

```bash
# Get transcript
./run tool/loom_api.py transcript https://www.loom.com/share/VIDEO_ID
./run tool/loom_api.py transcript VIDEO_ID --output-format text

# Get comments
./run tool/loom_api.py comments https://www.loom.com/share/VIDEO_ID
./run tool/loom_api.py comments VIDEO_ID --output-format text
```

## Output Formats

- `json` (default): Full structured data
- `text`: Human-readable formatted output

## Examples

```bash
# Get transcript as readable text
./run tool/loom_api.py transcript https://www.loom.com/share/abc123def456 -o text

# Get comments as JSON
./run tool/loom_api.py comments abc123def456
```

## Requirements

- Python 3.8+
- Node.js (for MCP server)
- Public Loom video URL

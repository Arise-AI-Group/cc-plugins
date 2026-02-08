# video-sop

Process time analysis and SOP extraction from screen recordings using Claude vision.

## What it does

Takes a screen recording video (any length, no audio needed) and produces:
- **process_analysis.md** — combined time analysis + procedure documentation
- **process_steps.json** — structured step data with timestamps, phases, decisions
- **process_flow.md** — Mermaid flowchart of the process

The primary output is a **process analysis report** with:
- Phase breakdown table (duration, % of total)
- Step timing table (duration per step, application, timestamp)
- Detailed procedure with inline timing badges

## Setup

```bash
brew install ffmpeg
./setup.sh
```

No API key needed — Claude Code analyzes frames directly using its built-in vision.

## Usage

```bash
# Extract frames from a screen recording
./run tool/video_sop.py extract-frames recording.mp4 -v

# Generate report from consolidated JSON (after Claude Code analysis)
./run tool/video_sop.py generate consolidated.json -o ./output/
```

## How it works

1. **Segment** long videos into chunks (ffmpeg)
2. **Extract** key frames at scene changes with perceptual dedup (ffmpeg + Pillow)
3. **Analyze** — Claude Code reads frames directly and identifies process steps with timestamps
4. **Generate** — process analysis report with time measurements, procedure, and flowchart

## Requirements

- Python 3.10+
- ffmpeg / ffprobe

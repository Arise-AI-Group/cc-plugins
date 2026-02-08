---
name: video-sop
description: This skill should be used when the user asks to "analyze a screen recording", "get time measurements from video", "how long does this process take", "time analysis of workflow", "create SOP from video", "extract steps from screen capture", "document a process from video walkthrough", "turn a video into an SOP", "measure process steps from video". Extracts process steps and timing data from screen recording videos using Claude vision analysis.
---

# Video Process Analysis — Time Measurement & SOP from Screen Recordings

## When to Use

**Trigger phrases:**
- "get time measurements from this process video"
- "how long does each step take in this recording"
- "analyze this screen recording"
- "time analysis of this workflow"
- "create an SOP from this video"
- "document the steps in this video walkthrough"

Use when you have a screen recording (no audio required) and need process timing data, step-by-step documentation, or both. The primary output is a **process analysis report** combining time measurements with procedure documentation.

## Tool

| Tool | Purpose |
|------|---------|
| `tool/video_sop.py` | Frame extraction and output generation |

## How It Works

Claude Code analyzes frames directly using its built-in vision — no separate API key needed.

**Step 1:** Extract frames from the video:
```bash
./run tool/video_sop.py extract-frames "path/to/recording.mp4" -v
```

**Step 2:** Read extracted frames using the Read tool (they are JPEG images). Read frames in batches of 10-15 at a time. For each batch, analyze what process steps are visible.

For each frame, identify:
- What application/window is active
- What the user did (clicked, typed, navigated)
- Specific UI elements, form fields, data visible
- Whether this is a decision point
- **The frame timestamp** (encoded in the filename: `frame_NNNN_123.45s.jpg` = 123.45 seconds into video)

**Step 3:** After analyzing all frames, consolidate the raw observations into structured JSON. **Each step MUST include `start_timestamp` and `end_timestamp`** (seconds into the video) so the report generator can compute durations.

```json
{
  "title": "Process Title",
  "purpose": "What this process accomplishes",
  "applications_used": ["App1", "App2"],
  "estimated_duration_minutes": 15,
  "phases": [
    {
      "phase_name": "Phase Name",
      "phase_description": "Brief description",
      "steps": [
        {
          "step_number": 1,
          "title": "Short title",
          "description": "Detailed description",
          "application": "App Name",
          "ui_details": "Menu > Settings > Advanced",
          "screenshot_ref": "frame_XXXX.jpg",
          "start_timestamp": 45.0,
          "end_timestamp": 120.5,
          "duration_seconds": 75.5,
          "is_decision_point": false,
          "decision_description": null,
          "is_critical": true,
          "substeps": [],
          "notes": ""
        }
      ]
    }
  ],
  "decision_points": [],
  "loops_identified": []
}
```

**Timing rules:**
- `start_timestamp`: the timestamp (in seconds) of the first frame showing this step
- `end_timestamp`: the timestamp of the last frame before the next step begins
- `duration_seconds`: optional, auto-computed from start/end if omitted
- Use the timestamps from frame filenames (e.g., `frame_0012_345.67s.jpg` = 345.67s)
- For the last step in a phase, use the timestamp of its last visible frame as end

**Step 4:** Save the consolidated JSON and run output generation:
```bash
./run tool/video_sop.py generate "path/to/consolidated.json" -o ./output/
```

This produces `process_analysis.md` — a combined report with time analysis tables and detailed procedure.

For large frame sets, use the Task tool to spawn parallel subagents — each analyzing a batch of 10-15 frames, then merge results.

## Quick Reference

```bash
# Extract frames from a video
./run tool/video_sop.py extract-frames "recording.mp4" -v

# Generate outputs from consolidated JSON
./run tool/video_sop.py generate "consolidated.json" -o ./output/

# Custom tuning for slow workflows
./run tool/video_sop.py extract-frames "recording.mp4" --scene-threshold 0.2 --min-interval 3
```

## Key Options

| Flag | Default | Description |
|------|---------|-------------|
| `--scene-threshold` | 0.3 | Scene detection sensitivity (lower = more frames) |
| `--min-interval` | 5 | Minimum seconds between frames |
| `--chunk-duration` | 600 | Chunk duration in seconds for long videos |
| `--format` | json markdown mermaid | Output formats to generate |
| `--include-screenshots` | off | Embed frame refs in report |

## Tuning Guide

| Scenario | `--scene-threshold` | `--min-interval` |
|----------|---------------------|-------------------|
| Fast clicking, many windows | 0.4 | 8 |
| Slow, methodical workflow | 0.2 | 3 |
| Data entry heavy | 0.15 | 5 |
| Video calls with screen sharing | 0.3 | 5 |
| Default / unknown | 0.3 | 5 |

## Outputs

| File | Description |
|------|-------------|
| `output/process_analysis.md` | Process report with time analysis + procedure |
| `output/process_steps.json` | Structured step data with phases, timing, decisions |
| `output/process_flow.md` | Mermaid flowchart of the process |
| `output/process_flow.json` | Draw.io compatible diagram JSON (if `--format drawio`) |

## Cross-Plugin Integration

To convert report to Word document (via doc-gen plugin):
```bash
cd ../doc-gen && ./run tool/doc_gen.py docx /path/to/output/process_analysis.md -o report.docx
```

To render Draw.io diagram (via diagrams plugin):
```bash
cd ../diagrams && ./run tool/generate_drawio.py /path/to/output/process_flow.json --style dark-modern -o process.drawio
```

## Environment

**System dependencies:** `ffmpeg` and `ffprobe` — install with `brew install ffmpeg`

No API key required — Claude Code analyzes frames directly using its built-in vision.

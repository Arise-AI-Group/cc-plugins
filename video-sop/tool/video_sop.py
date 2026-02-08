#!/usr/bin/env python3
"""Video-to-SOP Pipeline

Extracts key frames from screen recording videos and generates structured
process documentation from consolidated analysis JSON.

Claude Code analyzes the frames directly using its built-in vision
capability — no separate API key needed.

Usage:
    ./run tool/video_sop.py extract-frames recording.mp4 -v
    ./run tool/video_sop.py generate consolidated.json -o ./output/
"""

import argparse
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_SCENE_THRESHOLD = 0.3
DEFAULT_MIN_INTERVAL = 5.0
DEFAULT_CHUNK_DURATION = 600
MAX_IMAGE_DIMENSION = 1568


# ---------------------------------------------------------------------------
# System dependency checks
# ---------------------------------------------------------------------------

def check_system_deps():
    """Verify ffmpeg and ffprobe are available."""
    for cmd in ("ffmpeg", "ffprobe"):
        if not shutil.which(cmd):
            print(f"Error: {cmd} is required but not found.", file=sys.stderr)
            print("Install with: brew install ffmpeg", file=sys.stderr)
            sys.exit(1)


# ---------------------------------------------------------------------------
# Phase 1: Video Segmentation
# ---------------------------------------------------------------------------

def get_video_info(video_path: str) -> dict:
    """Get video metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,codec_name",
        "-show_entries", "format=duration",
        "-of", "json",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    stream = data.get("streams", [{}])[0]
    fmt = data.get("format", {})

    # Parse frame rate fraction (e.g. "30/1")
    fps_str = stream.get("r_frame_rate", "30/1")
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den) if float(den) else 30.0
    else:
        fps = float(fps_str)

    return {
        "duration": float(fmt.get("duration", 0)),
        "width": int(stream.get("width", 1920)),
        "height": int(stream.get("height", 1080)),
        "fps": fps,
        "codec": stream.get("codec_name", "unknown"),
    }


def segment_video(video_path: str, work_dir: str, chunk_duration: int = DEFAULT_CHUNK_DURATION,
                   verbose: bool = False) -> list[str]:
    """Split video into chunks. Returns list of chunk paths."""
    info = get_video_info(video_path)
    duration = info["duration"]

    if duration <= chunk_duration:
        if verbose:
            print(f"  Video is {duration:.0f}s, no chunking needed", file=sys.stderr)
        return [os.path.abspath(video_path)]

    chunks_dir = os.path.join(work_dir, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    num_chunks = math.ceil(duration / chunk_duration)
    if verbose:
        print(f"  Splitting {duration:.0f}s video into {num_chunks} chunks ({chunk_duration}s each)",
              file=sys.stderr)

    chunk_paths = []
    for i in range(num_chunks):
        start = i * chunk_duration
        chunk_path = os.path.join(chunks_dir, f"chunk_{i:03d}.mp4")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-ss", str(start), "-t", str(chunk_duration),
            "-c", "copy",
            "-loglevel", "error",
            chunk_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        chunk_paths.append(chunk_path)

    return chunk_paths


# ---------------------------------------------------------------------------
# Phase 2: Frame Extraction
# ---------------------------------------------------------------------------

def resize_frame(image_path: str, max_dimension: int = MAX_IMAGE_DIMENSION) -> str:
    """Resize image so longest side <= max_dimension. Overwrites in place."""
    from PIL import Image

    img = Image.open(image_path)
    w, h = img.size
    if max(w, h) <= max_dimension:
        return image_path

    ratio = max_dimension / max(w, h)
    new_size = (int(w * ratio), int(h * ratio))
    img = img.resize(new_size, Image.LANCZOS)
    img.save(image_path, quality=85, optimize=True)
    return image_path


def compute_frame_hash(image_path: str, hash_size: int = 16) -> list[int]:
    """Compute a perceptual hash (average hash) for deduplication.

    Resizes to hash_size x hash_size, converts to grayscale, compares each
    pixel to the mean. Returns a list of 0/1 values.
    """
    from PIL import Image

    img = Image.open(image_path).convert("L").resize(
        (hash_size, hash_size), Image.LANCZOS
    )
    pixels = list(img.tobytes())
    mean = sum(pixels) / len(pixels)
    return [1 if p > mean else 0 for p in pixels]


def hamming_distance(hash1: list[int], hash2: list[int]) -> int:
    """Count differing bits between two hashes."""
    return sum(a != b for a, b in zip(hash1, hash2))


def dedup_frames(frames: list[dict], similarity_threshold: float = 0.90,
                  verbose: bool = False) -> list[dict]:
    """Remove near-duplicate frames using perceptual hashing.

    similarity_threshold: 0.0-1.0, higher = more aggressive dedup.
        0.90 means frames must differ by >10% of hash bits to be kept.
    """
    if not frames:
        return frames

    hash_size = 16
    total_bits = hash_size * hash_size
    max_same_bits = int(total_bits * similarity_threshold)

    kept = [frames[0]]
    prev_hash = compute_frame_hash(frames[0]["path"], hash_size)

    for frame in frames[1:]:
        curr_hash = compute_frame_hash(frame["path"], hash_size)
        dist = hamming_distance(prev_hash, curr_hash)
        same_bits = total_bits - dist

        if same_bits <= max_same_bits:
            # Sufficiently different — keep it
            kept.append(frame)
            prev_hash = curr_hash
        else:
            # Too similar — skip and delete the file
            try:
                os.remove(frame["path"])
            except OSError:
                pass

    if verbose:
        print(f"  Dedup: {len(frames)} -> {len(kept)} frames "
              f"({len(frames) - len(kept)} duplicates removed)", file=sys.stderr)

    return kept


def extract_frames_for_video(video_path: str, output_dir: str,
                              scene_threshold: float = DEFAULT_SCENE_THRESHOLD,
                              min_interval: float = DEFAULT_MIN_INTERVAL,
                              time_offset: float = 0.0,
                              verbose: bool = False) -> list[dict]:
    """Extract key frames from a single video file using scene detection.

    Returns list of {"path": str, "timestamp": float} sorted by timestamp.
    """
    os.makedirs(output_dir, exist_ok=True)

    info = get_video_info(video_path)
    duration = info["duration"]

    # Step 1: Use ffmpeg to extract scene-change frames
    tmp_pattern = os.path.join(output_dir, "tmp_scene_%04d.jpg")

    # Build scene detection filter
    select_expr = f"select='gt(scene\\,{scene_threshold})'"

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"{select_expr},showinfo",
        "-vsync", "vfr",
        "-q:v", "2",
        "-loglevel", "info",
        tmp_pattern,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse timestamps from showinfo output (in stderr)
    timestamps = []
    for line in result.stderr.split("\n"):
        if "showinfo" in line and "pts_time:" in line:
            match = re.search(r"pts_time:\s*([\d.]+)", line)
            if match:
                timestamps.append(float(match.group(1)))

    # Step 2: Enforce minimum interval between frames
    filtered_timestamps = []
    last_ts = -min_interval
    for ts in sorted(timestamps):
        if ts - last_ts >= min_interval:
            filtered_timestamps.append(ts)
            last_ts = ts

    # Step 3: Fallback — if too few frames, supplement with interval sampling
    min_expected = max(3, int(duration / 30))
    if len(filtered_timestamps) < min_expected and duration > 5:
        interval = min(min_interval, duration / min_expected)
        t = 0.0
        while t < duration:
            if not any(abs(t - et) < min_interval * 0.5 for et in filtered_timestamps):
                filtered_timestamps.append(t)
            t += interval
        filtered_timestamps = sorted(set(filtered_timestamps))
        final = []
        last_ts = -min_interval
        for ts in filtered_timestamps:
            if ts - last_ts >= min_interval:
                final.append(ts)
                last_ts = ts
        filtered_timestamps = final

    # Always include the first frame if not already present
    if filtered_timestamps and filtered_timestamps[0] > 1.0:
        filtered_timestamps.insert(0, 0.5)
    elif not filtered_timestamps:
        filtered_timestamps = [0.5]

    if verbose:
        print(f"  Scene detection found {len(timestamps)} changes, "
              f"filtered to {len(filtered_timestamps)} frames", file=sys.stderr)

    # Clean up temp scene files
    for f in glob.glob(os.path.join(output_dir, "tmp_scene_*.jpg")):
        os.remove(f)

    # Step 4: Extract frames at the filtered timestamps
    frames = []
    for i, ts in enumerate(filtered_timestamps):
        abs_ts = ts + time_offset
        filename = f"frame_{i:04d}_{abs_ts:.2f}s.jpg"
        frame_path = os.path.join(output_dir, filename)
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(ts),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            "-loglevel", "error",
            frame_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        resize_frame(frame_path, MAX_IMAGE_DIMENSION)

        frames.append({
            "path": frame_path,
            "timestamp": abs_ts,
            "filename": filename,
        })

    return frames


def extract_all_frames(chunk_paths: list[str], work_dir: str,
                        scene_threshold: float = DEFAULT_SCENE_THRESHOLD,
                        min_interval: float = DEFAULT_MIN_INTERVAL,
                        verbose: bool = False) -> list[dict]:
    """Extract frames from all video chunks with corrected timestamps."""
    frames_dir = os.path.join(work_dir, "frames")
    all_frames = []

    for idx, chunk_path in enumerate(chunk_paths):
        chunk_name = Path(chunk_path).stem
        chunk_frames_dir = os.path.join(frames_dir, chunk_name) if len(chunk_paths) > 1 else frames_dir

        if len(chunk_paths) > 1:
            time_offset = idx * DEFAULT_CHUNK_DURATION
        else:
            time_offset = 0.0

        if verbose:
            print(f"  Extracting frames from chunk {idx + 1}/{len(chunk_paths)}...",
                  file=sys.stderr)

        chunk_frames = extract_frames_for_video(
            chunk_path, chunk_frames_dir,
            scene_threshold=scene_threshold,
            min_interval=min_interval,
            time_offset=time_offset,
            verbose=verbose,
        )
        all_frames.extend(chunk_frames)

    all_frames.sort(key=lambda f: f["timestamp"])

    if verbose:
        print(f"  Total frames extracted (pre-dedup): {len(all_frames)}", file=sys.stderr)

    all_frames = dedup_frames(all_frames, similarity_threshold=0.90, verbose=verbose)

    return all_frames


def load_frames_from_directory(frames_dir: str) -> list[dict]:
    """Load frame metadata from a pre-existing frames directory."""
    frames = []
    pattern = os.path.join(frames_dir, "**", "frame_*.jpg")
    for path in sorted(glob.glob(pattern, recursive=True)):
        filename = os.path.basename(path)
        match = re.match(r"frame_\d+_(\d+\.\d+)s\.jpg", filename)
        ts = float(match.group(1)) if match else 0.0
        frames.append({
            "path": path,
            "timestamp": ts,
            "filename": filename,
        })
    frames.sort(key=lambda f: f["timestamp"])
    return frames


# ---------------------------------------------------------------------------
# Output Generation
# ---------------------------------------------------------------------------

def _fmt_duration(seconds: float) -> str:
    """Format seconds as human-readable duration (e.g., '2m 30s', '1h 15m')."""
    if seconds < 0:
        return "—"
    seconds = round(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m {secs:02d}s" if secs else f"{minutes}m"
    hours = minutes // 60
    mins = minutes % 60
    if secs:
        return f"{hours}h {mins:02d}m {secs:02d}s"
    return f"{hours}h {mins:02d}m" if mins else f"{hours}h"


def _fmt_timestamp(seconds: float) -> str:
    """Format a video timestamp as MM:SS or H:MM:SS."""
    if seconds < 0:
        return "—"
    seconds = round(seconds)
    if seconds < 3600:
        return f"{seconds // 60}:{seconds % 60:02d}"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02d}:{s:02d}"


def _compute_timing(consolidated: dict) -> dict:
    """Extract timing data from consolidated steps.

    Each step should have start_timestamp and end_timestamp (seconds into video).
    Returns timing summary dict.
    """
    all_steps = []
    phase_timing = []

    for phase in consolidated.get("phases", []):
        phase_steps = phase.get("steps", [])
        p_start = None
        p_end = None

        for step in phase_steps:
            start = step.get("start_timestamp")
            end = step.get("end_timestamp")
            dur = step.get("duration_seconds")

            # Compute duration if we have start/end but not explicit duration
            if dur is None and start is not None and end is not None:
                dur = end - start
            elif dur is None:
                dur = -1  # unknown

            if start is not None:
                if p_start is None:
                    p_start = start
                p_end = end if end is not None else start

            all_steps.append({
                "step_number": step.get("step_number"),
                "title": step.get("title", step.get("action", "")),
                "application": step.get("application", ""),
                "start": start,
                "end": end,
                "duration": dur if dur is not None and dur >= 0 else None,
                "phase": phase.get("phase_name", ""),
            })

        p_dur = None
        if p_start is not None and p_end is not None:
            p_dur = p_end - p_start

        phase_timing.append({
            "phase_name": phase.get("phase_name", ""),
            "start": p_start,
            "end": p_end,
            "duration": p_dur,
            "step_count": len(phase_steps),
        })

    # Total process duration
    timed_steps = [s for s in all_steps if s["start"] is not None]
    if timed_steps:
        total_start = min(s["start"] for s in timed_steps)
        total_end = max(s["end"] for s in timed_steps if s["end"] is not None)
        total_dur = total_end - total_start if total_end is not None else None
    else:
        total_start = None
        total_end = None
        total_dur = consolidated.get("estimated_duration_minutes")
        if total_dur:
            total_dur = total_dur * 60

    return {
        "steps": all_steps,
        "phases": phase_timing,
        "total_start": total_start,
        "total_end": total_end,
        "total_duration": total_dur,
        "has_timestamps": len(timed_steps) > 0,
    }


def generate_json_output(consolidated: dict, output_path: str) -> str:
    """Write consolidated process data as pretty-printed JSON."""
    with open(output_path, "w") as f:
        json.dump(consolidated, f, indent=2)
    return output_path


def generate_process_report(consolidated: dict, output_path: str,
                             include_screenshots: bool = False) -> str:
    """Generate a combined process & time analysis report."""
    lines = []
    title = consolidated.get("title", "Process Analysis")
    timing = _compute_timing(consolidated)

    # --- Header ---
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d')}  ")
    lines.append(f"**Source:** Screen recording analysis  ")
    if timing["total_duration"] is not None:
        lines.append(f"**Observed Duration:** {_fmt_duration(timing['total_duration'])}  ")
    elif consolidated.get("estimated_duration_minutes"):
        lines.append(f"**Estimated Duration:** {consolidated['estimated_duration_minutes']} minutes  ")
    if timing["total_start"] is not None:
        lines.append(f"**Video Range:** {_fmt_timestamp(timing['total_start'])} "
                     f"— {_fmt_timestamp(timing['total_end'])}  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    if consolidated.get("purpose"):
        lines.append(consolidated["purpose"])
        lines.append("")

    apps = consolidated.get("applications_used", [])
    if apps:
        lines.append(f"**Applications:** {', '.join(apps)}")
        lines.append("")

    # --- Time Analysis Summary ---
    if timing["has_timestamps"]:
        lines.append("## Time Analysis")
        lines.append("")

        # Phase breakdown table
        if timing["phases"]:
            lines.append("### Phase Breakdown")
            lines.append("")
            lines.append("| Phase | Steps | Duration | % of Total | Start | End |")
            lines.append("|-------|------:|:--------:|:----------:|:-----:|:---:|")
            for pt in timing["phases"]:
                pct = ""
                if pt["duration"] is not None and timing["total_duration"] and timing["total_duration"] > 0:
                    pct = f"{pt['duration'] / timing['total_duration'] * 100:.0f}%"
                dur_str = _fmt_duration(pt["duration"]) if pt["duration"] is not None else "—"
                start_str = _fmt_timestamp(pt["start"]) if pt["start"] is not None else "—"
                end_str = _fmt_timestamp(pt["end"]) if pt["end"] is not None else "—"
                lines.append(f"| {pt['phase_name']} | {pt['step_count']} | {dur_str} "
                             f"| {pct} | {start_str} | {end_str} |")
            if timing["total_duration"] is not None:
                lines.append(f"| **Total** | **{len(timing['steps'])}** "
                             f"| **{_fmt_duration(timing['total_duration'])}** "
                             f"| **100%** | | |")
            lines.append("")

        # Step timing table
        lines.append("### Step Timing")
        lines.append("")
        lines.append("| # | Step | Application | Duration | Timestamp |")
        lines.append("|--:|------|-------------|:--------:|:---------:|")
        for s in timing["steps"]:
            dur_str = _fmt_duration(s["duration"]) if s["duration"] is not None else "—"
            ts_str = _fmt_timestamp(s["start"]) if s["start"] is not None else "—"
            lines.append(f"| {s['step_number']} | {s['title']} | {s['application']} "
                         f"| {dur_str} | {ts_str} |")
        lines.append("")

    # --- Detailed Procedure ---
    lines.append("## Procedure")
    lines.append("")

    global_step = 0
    for phase in consolidated.get("phases", []):
        phase_name = phase.get("phase_name", "")
        if phase_name:
            # Find phase timing
            pt = next((p for p in timing["phases"] if p["phase_name"] == phase_name), None)
            dur_suffix = ""
            if pt and pt["duration"] is not None:
                dur_suffix = f" ({_fmt_duration(pt['duration'])})"
            lines.append(f"### {phase_name}{dur_suffix}")
            lines.append("")
            if phase.get("phase_description"):
                lines.append(f"_{phase['phase_description']}_")
                lines.append("")

        for step in phase.get("steps", []):
            global_step += 1
            step_title = step.get("title", step.get("action", "Step"))

            # Build timing badge
            time_badge = ""
            dur = step.get("duration_seconds")
            start = step.get("start_timestamp")
            end = step.get("end_timestamp")
            if dur is None and start is not None and end is not None:
                dur = end - start
            if dur is not None and dur >= 0:
                time_badge = f" `{_fmt_duration(dur)}`"
            elif start is not None:
                time_badge = f" `@{_fmt_timestamp(start)}`"

            lines.append(f"**Step {global_step}: {step_title}**{time_badge}")
            lines.append("")

            if step.get("description"):
                lines.append(step["description"])
                lines.append("")

            if step.get("ui_details"):
                lines.append(f"> **UI Path:** {step['ui_details']}")
                lines.append("")

            if step.get("substeps"):
                for sub in step["substeps"]:
                    lines.append(f"   - {sub}")
                lines.append("")

            if step.get("is_decision_point") and step.get("decision_description"):
                lines.append(f"> **Decision Point:** {step['decision_description']}")
                lines.append("")

            if step.get("notes"):
                lines.append(f"> **Note:** {step['notes']}")
                lines.append("")

            if include_screenshots and step.get("screenshot_ref"):
                lines.append(f"![Step {global_step}](frames/{step['screenshot_ref']})")
                lines.append("")

    # --- Decision Points ---
    decisions = consolidated.get("decision_points", [])
    if decisions:
        lines.append("---")
        lines.append("")
        lines.append("## Decision Points")
        lines.append("")
        lines.append("| Step | Condition | Options | Action |")
        lines.append("|------|-----------|---------|--------|")
        for dp in decisions:
            opts = ", ".join(dp.get("options", [])) if dp.get("options") else ""
            lines.append(f"| {dp.get('step_number', '')} | {dp.get('condition', '')} "
                         f"| {opts} | {dp.get('action', '')} |")
        lines.append("")

    # --- Repeated Patterns ---
    loops = consolidated.get("loops_identified", [])
    if loops:
        lines.append("## Repeated Patterns")
        lines.append("")
        for loop in loops:
            steps_str = ", ".join(str(s) for s in loop.get("steps_involved", []))
            lines.append(f"- **{loop.get('description', '')}** "
                         f"(Steps {steps_str}, ~{loop.get('estimated_repetitions', '?')}x)")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by video-sop on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    return output_path


def generate_mermaid_flowchart(consolidated: dict, output_path: str) -> str:
    """Generate a Mermaid flowchart from consolidated steps."""
    lines = ["flowchart TD"]
    lines.append('    Start(["Start"])')

    step_ids = []
    all_steps = []
    for phase in consolidated.get("phases", []):
        for step in phase.get("steps", []):
            all_steps.append(step)

    for step in all_steps:
        sid = f"s{step['step_number']}"
        label = step.get("title", step.get("action", f"Step {step['step_number']}"))
        label = label.replace('"', "'")

        if step.get("is_decision_point"):
            lines.append(f'    {sid}{{{{{label}}}}}')
        else:
            lines.append(f'    {sid}["{step["step_number"]}. {label}"]')
        step_ids.append(sid)

    lines.append('    End(["End"])')
    lines.append("")

    prev = "Start"
    for sid in step_ids:
        lines.append(f"    {prev} --> {sid}")
        prev = sid
    lines.append(f"    {prev} --> End")

    for dp in consolidated.get("decision_points", []):
        sid = f"s{dp['step_number']}"
        if dp.get("action"):
            lines.append(f"    {sid} -.->|{dp.get('condition', 'alt')}| End")

    for loop in consolidated.get("loops_identified", []):
        involved = loop.get("steps_involved", [])
        if len(involved) >= 2:
            last = f"s{involved[-1]}"
            first = f"s{involved[0]}"
            lines.append(f"    {last} -.->|repeat| {first}")

    mermaid_text = "\n".join(lines)

    with open(output_path, "w") as f:
        f.write(f"# Process Flow\n\n```mermaid\n{mermaid_text}\n```\n")
    return output_path


def generate_drawio_json(consolidated: dict, output_path: str) -> str:
    """Generate JSON compatible with the diagrams plugin's generate_drawio.py."""
    nodes = [{"id": "start", "label": "Start", "shape": "ellipse"}]
    connections = []

    all_steps = []
    for phase in consolidated.get("phases", []):
        for step in phase.get("steps", []):
            all_steps.append(step)

    for step in all_steps:
        sid = f"step{step['step_number']}"
        shape = "diamond" if step.get("is_decision_point") else "rectangle"
        nodes.append({
            "id": sid,
            "label": f"{step['step_number']}. {step.get('title', '')}",
            "shape": shape,
        })

    nodes.append({"id": "end", "label": "End", "shape": "ellipse"})

    prev = "start"
    for step in all_steps:
        sid = f"step{step['step_number']}"
        connections.append({"from": prev, "to": sid})
        prev = sid
    connections.append({"from": prev, "to": "end"})

    groups = []
    for phase in consolidated.get("phases", []):
        group_nodes = [f"step{s['step_number']}" for s in phase.get("steps", [])]
        if group_nodes:
            groups.append({
                "id": f"phase_{phase.get('phase_name', '').lower().replace(' ', '_')}",
                "label": phase.get("phase_name", ""),
                "children": group_nodes,
            })

    diagram = {
        "type": "flowchart",
        "title": consolidated.get("title", "Process Flow"),
        "direction": "TD",
        "nodes": nodes,
        "connections": connections,
    }
    if groups:
        diagram["groups"] = groups

    with open(output_path, "w") as f:
        json.dump(diagram, f, indent=2)
    return output_path


# ---------------------------------------------------------------------------
# Orchestrators
# ---------------------------------------------------------------------------

def run_extract_frames(args) -> None:
    """Execute phases 1-2: segment video and extract key frames."""
    check_system_deps()

    video_path = os.path.abspath(args.video_file)
    if not os.path.isfile(video_path):
        print(f"Error: Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    work_dir = os.path.abspath(args.output_dir) if args.output_dir else os.path.join(
        os.path.dirname(video_path), "video-sop-work"
    )
    os.makedirs(work_dir, exist_ok=True)
    verbose = args.verbose

    print("[Phase 1] Video Segmentation", file=sys.stderr)
    video_info = get_video_info(video_path)
    print(f"  Video: {video_info['duration']:.0f}s, "
          f"{video_info['width']}x{video_info['height']}", file=sys.stderr)

    chunks = segment_video(video_path, work_dir, args.chunk_duration, verbose)

    print("\n[Phase 2] Frame Extraction", file=sys.stderr)
    frames = extract_all_frames(
        chunks, work_dir,
        scene_threshold=args.scene_threshold,
        min_interval=args.min_interval,
        verbose=verbose,
    )
    print(f"  Frames extracted: {len(frames)}", file=sys.stderr)

    frames_dir = os.path.join(work_dir, "frames")
    print(f"\nFrames saved to: {frames_dir}", file=sys.stderr)
    print(frames_dir)


def run_generate(args) -> None:
    """Generate outputs from a pre-built consolidated JSON file."""
    json_path = os.path.abspath(args.json_file)
    if not os.path.isfile(json_path):
        print(f"Error: JSON file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    with open(json_path) as f:
        consolidated = json.load(f)

    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    formats = args.format

    print("Generating outputs...", file=sys.stderr)

    if "json" in formats:
        path = generate_json_output(consolidated, os.path.join(output_dir, "process_steps.json"))
        print(f"  JSON:     {path}", file=sys.stderr)
    if "markdown" in formats:
        path = generate_process_report(
            consolidated, os.path.join(output_dir, "process_analysis.md"),
            include_screenshots=args.include_screenshots,
        )
        print(f"  Report:   {path}", file=sys.stderr)
    if "mermaid" in formats:
        path = generate_mermaid_flowchart(consolidated, os.path.join(output_dir, "process_flow.md"))
        print(f"  Mermaid: {path}", file=sys.stderr)
    if "drawio" in formats:
        path = generate_drawio_json(consolidated, os.path.join(output_dir, "process_flow.json"))
        print(f"  DrawIO:  {path}", file=sys.stderr)

    print(f"\nDone! Outputs in: {output_dir}", file=sys.stderr)
    print(output_dir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract frames from screen recordings and generate SOP outputs"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- extract-frames ---
    ef = subparsers.add_parser("extract-frames",
                                help="Extract key frames from a screen recording")
    ef.add_argument("video_file", help="Path to screen recording video")
    ef.add_argument("-o", "--output-dir", help="Output directory (default: alongside video)")
    ef.add_argument("--scene-threshold", type=float, default=DEFAULT_SCENE_THRESHOLD,
                    help=f"Scene change threshold 0.0-1.0 (default: {DEFAULT_SCENE_THRESHOLD})")
    ef.add_argument("--min-interval", type=float, default=DEFAULT_MIN_INTERVAL,
                    help=f"Min seconds between frames (default: {DEFAULT_MIN_INTERVAL})")
    ef.add_argument("--chunk-duration", type=int, default=DEFAULT_CHUNK_DURATION,
                    help=f"Video chunk duration in seconds (default: {DEFAULT_CHUNK_DURATION})")
    ef.add_argument("-v", "--verbose", action="store_true")

    # --- generate ---
    gen = subparsers.add_parser("generate",
                                help="Generate SOP outputs from consolidated JSON")
    gen.add_argument("json_file", help="Path to consolidated process_steps.json")
    gen.add_argument("-o", "--output-dir", help="Output directory",
                     default="./video-sop-work/output")
    gen.add_argument("--format", nargs="+", default=["json", "markdown", "mermaid"],
                     choices=["json", "markdown", "mermaid", "drawio"])
    gen.add_argument("--include-screenshots", action="store_true",
                     help="Embed screenshot references in the SOP")

    args = parser.parse_args()

    if args.command == "extract-frames":
        run_extract_frames(args)
    elif args.command == "generate":
        run_generate(args)


if __name__ == "__main__":
    main()

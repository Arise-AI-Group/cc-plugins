#!/usr/bin/env python3
"""
Transcribe audio files using OpenAI Whisper API.

Handles large files by chunking (Whisper has 25MB limit).
Saves transcript alongside the original audio file.

Usage:
    ./run tool/transcribe_audio.py "path/to/audio.mp3"
    ./run tool/transcribe_audio.py "path/to/audio.mp3" --output "custom_output.txt"

Output:
    Creates {original_name}_transcript.txt in the same directory as the audio file.
"""

import sys
import os
import argparse
import tempfile
from pathlib import Path
from openai import OpenAI

from .config import get_api_key

# Whisper API file size limit (25MB)
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB in bytes


def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    return os.path.getsize(file_path)


def get_audio_duration(file_path: str) -> float:
    """
    Get audio duration in seconds using ffprobe.

    Returns:
        Duration in seconds
    """
    import subprocess
    import json

    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_format', file_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError) as e:
        print(f"Error getting audio duration: {e}", file=sys.stderr)
        sys.exit(1)


def chunk_audio(file_path: str, max_size_mb: int = 24) -> list[str]:
    """
    Split audio file into chunks if it exceeds the size limit.
    Uses ffmpeg directly (compatible with Python 3.14+).

    Returns:
        List of file paths (original if small enough, or temp chunk files)
    """
    import subprocess
    import shutil

    file_size = get_file_size(file_path)
    max_size_bytes = max_size_mb * 1024 * 1024

    if file_size <= max_size_bytes:
        print(f"File size ({file_size / 1024 / 1024:.1f}MB) is within limit, no chunking needed.", file=sys.stderr)
        return [file_path]

    print(f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds {max_size_mb}MB limit. Chunking...", file=sys.stderr)

    # Check for ffmpeg
    if not shutil.which('ffmpeg'):
        print("Error: ffmpeg is required for chunking large files.", file=sys.stderr)
        print("Install it with: brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    # Get audio duration
    duration = get_audio_duration(file_path)
    print(f"Audio duration: {duration / 60:.1f} minutes", file=sys.stderr)

    # Calculate chunk duration based on target output size at 128kbps
    # 128kbps = 16KB/sec = ~0.96MB/min
    # Target 20MB chunks to stay safely under 25MB limit
    target_chunk_mb = 20
    mb_per_minute = 0.96  # at 128kbps
    max_chunk_duration_min = target_chunk_mb / mb_per_minute  # ~20.8 minutes per chunk

    num_chunks = max(1, int(duration / 60 / max_chunk_duration_min) + 1)
    chunk_duration_sec = duration / num_chunks

    print(f"Splitting into ~{num_chunks} chunks of ~{chunk_duration_sec / 60:.1f} minutes each...", file=sys.stderr)

    chunk_files = []
    temp_dir = tempfile.mkdtemp(prefix="audio_chunks_")

    for i in range(num_chunks):
        start_sec = i * chunk_duration_sec
        # For the last chunk, go to the end
        if i == num_chunks - 1:
            duration_arg = []  # No duration limit for last chunk
        else:
            duration_arg = ['-t', str(chunk_duration_sec)]

        chunk_path = os.path.join(temp_dir, f"chunk_{i:03d}.mp3")

        cmd = [
            'ffmpeg', '-y', '-i', file_path,
            '-ss', str(start_sec),
            *duration_arg,
            '-acodec', 'libmp3lame', '-b:a', '128k',
            '-loglevel', 'error',
            chunk_path
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            chunk_files.append(chunk_path)
            end_sec = start_sec + chunk_duration_sec if i < num_chunks - 1 else duration
            print(f"  Created chunk {i + 1}/{num_chunks}: {start_sec / 60:.1f}min - {end_sec / 60:.1f}min", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Error creating chunk {i + 1}: {e.stderr.decode()}", file=sys.stderr)
            sys.exit(1)

    return chunk_files


def transcribe_file(client: OpenAI, file_path: str) -> str:
    """
    Transcribe a single audio file using Whisper API.

    Returns:
        Transcription text
    """
    with open(file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return response


def transcribe_audio(file_path: str, output_path: str = None) -> str:
    """
    Transcribe an audio file, handling chunking if necessary.

    Args:
        file_path: Path to the audio file
        output_path: Optional custom output path for the transcript

    Returns:
        Path to the transcript file
    """
    # Validate input file
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment.", file=sys.stderr)
        print("Please add it to your .env file.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # Determine output path
    if output_path is None:
        input_path = Path(file_path)
        output_path = str(input_path.parent / f"{input_path.stem}_transcript.txt")

    print(f"Transcribing: {file_path}", file=sys.stderr)
    print(f"Output will be saved to: {output_path}", file=sys.stderr)

    # Chunk if necessary
    chunk_files = chunk_audio(file_path)

    # Transcribe each chunk
    transcripts = []
    for i, chunk_path in enumerate(chunk_files):
        if len(chunk_files) > 1:
            print(f"Transcribing chunk {i + 1}/{len(chunk_files)}...", file=sys.stderr)
        else:
            print("Transcribing...", file=sys.stderr)

        transcript = transcribe_file(client, chunk_path)
        transcripts.append(transcript)

    # Combine transcripts
    full_transcript = "\n\n".join(transcripts)

    # Clean up temp files if we created chunks
    if len(chunk_files) > 1 and chunk_files[0] != file_path:
        temp_dir = os.path.dirname(chunk_files[0])
        for chunk_path in chunk_files:
            try:
                os.remove(chunk_path)
            except Exception:
                pass
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass
        print("Cleaned up temporary chunk files.", file=sys.stderr)

    # Save transcript
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_transcript)

    print(f"\nTranscription complete!", file=sys.stderr)
    print(f"Saved to: {output_path}", file=sys.stderr)
    print(f"Total length: {len(full_transcript):,} characters", file=sys.stderr)

    # Output the path for easy piping
    print(output_path)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio files using OpenAI Whisper API"
    )
    parser.add_argument(
        "audio_file",
        help="Path to the audio file to transcribe"
    )
    parser.add_argument(
        "--output", "-o",
        help="Custom output path for the transcript (default: {input_name}_transcript.txt)"
    )

    args = parser.parse_args()

    transcribe_audio(args.audio_file, args.output)


if __name__ == "__main__":
    main()

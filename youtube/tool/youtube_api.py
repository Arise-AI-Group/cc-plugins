#!/usr/bin/env python3
"""YouTube video transcript API client and CLI tool.

Retrieves transcripts and available languages from public YouTube videos.
No YouTube API key required.
"""

import argparse
import json
import re
import sys
from typing import Any, Optional

from youtube_transcript_api import YouTubeTranscriptApi


# =============================================================================
# Exceptions
# =============================================================================

class YouTubeTranscriptError(Exception):
    """Base exception for YouTube transcript errors."""
    pass


class VideoNotFoundError(YouTubeTranscriptError):
    """Video not found or not accessible."""
    pass


class NoTranscriptError(YouTubeTranscriptError):
    """No transcript available for the video."""
    pass


class InvalidURLError(YouTubeTranscriptError):
    """Invalid YouTube URL or video ID."""
    pass


# =============================================================================
# Client
# =============================================================================

class YouTubeClient:
    """Client for YouTube transcript retrieval."""

    # YouTube video IDs are exactly 11 characters: alphanumeric, dash, underscore
    _ID_PATTERN = r"[\w-]{11}"

    _URL_PATTERNS = [
        re.compile(r"(?:youtube\.com/watch\?.*v=)(" + _ID_PATTERN + ")"),
        re.compile(r"(?:youtu\.be/)(" + _ID_PATTERN + ")"),
        re.compile(r"(?:youtube\.com/shorts/)(" + _ID_PATTERN + ")"),
        re.compile(r"(?:youtube\.com/embed/)(" + _ID_PATTERN + ")"),
        re.compile(r"(?:youtube\.com/v/)(" + _ID_PATTERN + ")"),
    ]

    _BARE_ID_PATTERN = re.compile(r"^" + _ID_PATTERN + "$")

    def __init__(self):
        self.api = YouTubeTranscriptApi()

    @classmethod
    def extract_video_id(cls, url_or_id: str) -> str:
        """Extract video ID from various YouTube URL formats or bare ID.

        Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/shorts/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/v/VIDEO_ID
        - Bare 11-character video ID
        """
        url_or_id = url_or_id.strip()

        for pattern in cls._URL_PATTERNS:
            match = pattern.search(url_or_id)
            if match:
                return match.group(1)

        if cls._BARE_ID_PATTERN.match(url_or_id):
            return url_or_id

        raise InvalidURLError(
            f"Could not extract video ID from: {url_or_id}\n"
            "Expected a YouTube URL or 11-character video ID"
        )

    def get_transcript(
        self, url_or_id: str, lang: Optional[str] = None
    ) -> dict:
        """Get transcript from a YouTube video.

        Args:
            url_or_id: YouTube URL or video ID.
            lang: Language code (e.g. 'en', 'de'). If None, tries English
                  then falls back to the first available transcript.

        Returns:
            Dict with video_id, language, language_code, is_generated,
            and segments list.
        """
        video_id = self.extract_video_id(url_or_id)
        languages = [lang] if lang else ["en"]

        transcript = None

        try:
            transcript = self.api.fetch(video_id, languages=languages)
        except Exception as fetch_err:
            if lang:
                # User asked for a specific language — don't fall back
                raise NoTranscriptError(
                    f"No transcript in language '{lang}' for video {video_id}: {fetch_err}"
                ) from fetch_err

            # Default case: try listing all and pick the best match
            try:
                transcript_list = self.api.list(video_id)
                try:
                    found = transcript_list.find_transcript(["en"])
                    transcript = found.fetch()
                except Exception:
                    for t in transcript_list:
                        transcript = t.fetch()
                        break
            except Exception as e:
                raise NoTranscriptError(
                    f"No transcripts available for video {video_id}: {e}"
                ) from e

        if transcript is None:
            raise NoTranscriptError(
                f"No transcripts available for video {video_id}"
            )

        segments = [
            {
                "text": snippet.text,
                "start": snippet.start,
                "duration": snippet.duration,
            }
            for snippet in transcript
        ]

        return {
            "video_id": transcript.video_id,
            "language": transcript.language,
            "language_code": transcript.language_code,
            "is_generated": transcript.is_generated,
            "segments": segments,
        }

    def list_languages(self, url_or_id: str) -> dict:
        """List available transcript languages for a video.

        Args:
            url_or_id: YouTube URL or video ID.

        Returns:
            Dict with video_id and languages list.
        """
        video_id = self.extract_video_id(url_or_id)

        try:
            transcript_list = self.api.list(video_id)
        except Exception as e:
            raise NoTranscriptError(
                f"Could not list transcripts for video {video_id}: {e}"
            ) from e

        languages = [
            {
                "language": t.language,
                "language_code": t.language_code,
                "is_generated": t.is_generated,
                "is_translatable": t.is_translatable,
            }
            for t in transcript_list
        ]

        return {
            "video_id": video_id,
            "languages": languages,
        }


# =============================================================================
# Formatting
# =============================================================================

def format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS or MM:SS."""
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_transcript_text(data: dict) -> str:
    """Format transcript as readable markdown."""
    lines = [
        "# YouTube Transcript",
        "",
        f"**Video:** https://www.youtube.com/watch?v={data['video_id']}",
        f"**Language:** {data['language']} ({data['language_code']})",
    ]
    if data.get("is_generated"):
        lines.append("**Type:** Auto-generated")
    lines += ["", "---", ""]

    for seg in data.get("segments", []):
        ts = format_timestamp(seg["start"])
        lines.append(f"[{ts}] {seg['text']}")

    return "\n".join(lines)


def format_languages_text(data: dict) -> str:
    """Format language list as readable text."""
    lines = [f"Available transcripts for video {data['video_id']}:", ""]
    for lang in data.get("languages", []):
        kind = "(auto-generated)" if lang["is_generated"] else "(manual)"
        lines.append(f"  - {lang['language']} [{lang['language_code']}] {kind}")
    return "\n".join(lines)


def format_output(data: Any, fmt: str = "json") -> str:
    """Format output data as JSON or text."""
    if fmt == "json":
        return json.dumps(data, indent=2, default=str)
    return str(data)


# =============================================================================
# CLI
# =============================================================================

def cmd_transcript(args: argparse.Namespace) -> None:
    client = YouTubeClient()
    data = client.get_transcript(args.url, lang=args.lang)
    if args.output_format == "text":
        print(format_transcript_text(data))
    else:
        print(format_output(data))


def cmd_languages(args: argparse.Namespace) -> None:
    client = YouTubeClient()
    data = client.list_languages(args.url)
    if args.output_format == "text":
        print(format_languages_text(data))
    else:
        print(format_output(data))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="YouTube video transcript tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s transcript https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
            "  %(prog)s transcript dQw4w9WgXcQ --lang de -o text\n"
            "  %(prog)s languages https://youtu.be/dQw4w9WgXcQ\n"
        ),
    )
    parser.add_argument(
        "-o", "--output-format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    subs = parser.add_subparsers(dest="command", help="Available commands")

    fmt_kwargs = dict(
        type=str, choices=["json", "text"], default="json",
        help="Output format (default: json)",
    )

    tp = subs.add_parser("transcript", help="Get transcript from a YouTube video")
    tp.add_argument("url", help="YouTube video URL or video ID")
    tp.add_argument("-l", "--lang", default=None, help="Language code (default: en)")
    tp.add_argument("-o", "--output-format", **fmt_kwargs)
    tp.set_defaults(func=cmd_transcript)

    lp = subs.add_parser("languages", help="List available transcript languages")
    lp.add_argument("url", help="YouTube video URL or video ID")
    lp.add_argument("-o", "--output-format", **fmt_kwargs)
    lp.set_defaults(func=cmd_languages)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    try:
        args.func(args)
        return 0
    except InvalidURLError as e:
        print(f"Invalid URL: {e}", file=sys.stderr)
        return 1
    except NoTranscriptError as e:
        print(f"No transcript: {e}", file=sys.stderr)
        return 1
    except YouTubeTranscriptError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

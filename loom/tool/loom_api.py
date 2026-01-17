#!/usr/bin/env python3
"""Loom video transcript and comments API client and CLI tool.

Provides access to public Loom video features:
- Get full transcripts with timestamps
- Extract comments from videos
"""

import argparse
import json
import re
import sys
from typing import Any, Optional

import requests


# =============================================================================
# Exceptions
# =============================================================================


class LoomError(Exception):
    """Base exception for Loom API errors."""
    pass


class LoomNotFoundError(LoomError):
    """Video not found or not accessible."""
    pass


class LoomNetworkError(LoomError):
    """Network request failed."""
    pass


# =============================================================================
# GraphQL Queries
# =============================================================================

# Query to get video info
VIDEO_INFO_QUERY = """
query GetVideoInfo($videoId: ID!) {
  getVideo(id: $videoId) {
    ... on RegularUserVideo {
      id
      name
      createdAt
      description
      owner {
        display_name
      }
    }
    ... on PrivateVideo {
      id
    }
    ... on VideoPasswordMissingOrIncorrect {
      id
    }
  }
}
"""

# Query to get video transcript details (separate from video info)
TRANSCRIPT_QUERY = """
query FetchVideoTranscript($videoId: ID!) {
  fetchVideoTranscript(videoId: $videoId) {
    ... on VideoTranscriptDetails {
      idv2
      video_id
      source_url
      captions_source_url
      language
      transcription_status
    }
  }
}
"""

# Query to get video comments - NOTE: Comments API may have changed
COMMENTS_QUERY = """
query GetVideoComments($videoId: ID!) {
  getVideo(id: $videoId) {
    ... on RegularUserVideo {
      id
      name
    }
    ... on PrivateVideo {
      id
    }
    ... on VideoPasswordMissingOrIncorrect {
      id
    }
  }
}
"""


# =============================================================================
# Client
# =============================================================================


class LoomClient:
    """Client for Loom GraphQL API."""

    API_ENDPOINT = "https://www.loom.com/graphql"

    def __init__(self):
        """Initialize client."""
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://www.loom.com",
            "Referer": "https://www.loom.com/",
        })

    @staticmethod
    def extract_video_id(url: str) -> str:
        """Extract video ID from a Loom URL.

        Supports formats:
        - https://www.loom.com/share/VIDEO_ID
        - https://www.loom.com/share/VIDEO_ID?...
        - https://loom.com/share/VIDEO_ID

        Args:
            url: Loom video URL

        Returns:
            Video ID string

        Raises:
            LoomError: If URL format is invalid
        """
        # Try to extract from share URL
        patterns = [
            r"loom\.com/share/([a-zA-Z0-9]+)",
            r"loom\.com/embed/([a-zA-Z0-9]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Maybe it's already just the ID
        if re.match(r"^[a-zA-Z0-9]+$", url):
            return url

        raise LoomError(
            f"Invalid Loom URL format: {url}\n"
            "Expected format: https://www.loom.com/share/VIDEO_ID"
        )

    def _request(self, query: str, variables: Optional[dict] = None) -> dict:
        """Make a GraphQL request to Loom API.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Response data dict

        Raises:
            LoomNetworkError: If request fails
            LoomNotFoundError: If video not found
            LoomError: For other API errors
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = self.session.post(
                self.API_ENDPOINT,
                json=payload,
                timeout=30,
            )
        except requests.RequestException as e:
            raise LoomNetworkError(f"Request failed: {e}") from e

        if response.status_code >= 400:
            raise LoomError(f"API error {response.status_code}: {response.text}")

        data = response.json()

        if "errors" in data:
            errors = data["errors"]
            error_msg = "; ".join(e.get("message", str(e)) for e in errors)
            if "not found" in error_msg.lower() or "null" in str(data.get("data")):
                raise LoomNotFoundError(f"Video not found or not accessible")
            raise LoomError(f"GraphQL errors: {error_msg}")

        return data.get("data", {})

    def get_transcript(self, url_or_id: str) -> dict:
        """Get transcript from a Loom video.

        Args:
            url_or_id: Loom video URL or video ID

        Returns:
            Dict with video info and transcript sentences
        """
        video_id = self.extract_video_id(url_or_id)

        # Get video info
        video_data = self._request(VIDEO_INFO_QUERY, {"videoId": video_id})
        video = video_data.get("getVideo")
        if not video or not video.get("name"):
            raise LoomNotFoundError(f"Video {video_id} not found or not accessible")

        # Get transcript details
        transcript_data = self._request(TRANSCRIPT_QUERY, {"videoId": video_id})
        transcript_details = transcript_data.get("fetchVideoTranscript")

        if not transcript_details or not transcript_details.get("source_url"):
            # No transcript available
            video["transcription"] = None
            return video

        # Fetch the actual transcript JSON from source_url
        try:
            response = self.session.get(transcript_details["source_url"], timeout=30)
            response.raise_for_status()
            transcript_json = response.json()

            # Transform to expected format - Loom uses 'phrases' with 'ts' and 'value'
            sentences = []
            phrases = transcript_json.get("phrases", [])
            for item in phrases:
                # ts is in seconds, convert to milliseconds for consistency
                start_ts = item.get("ts")
                start_ts_ms = int(start_ts * 1000) if start_ts is not None else None
                sentences.append({
                    "text": item.get("value", ""),
                    "speaker_name": "Speaker",  # Loom doesn't provide speaker identification
                    "start_ts": start_ts_ms,
                    "end_ts": None,
                })

            video["transcription"] = {
                "id": transcript_details.get("idv2"),
                "source_lang": transcript_details.get("language", "en"),
                "sentences": sentences,
            }
        except requests.RequestException as e:
            raise LoomNetworkError(f"Failed to fetch transcript: {e}") from e

        return video

    def get_comments(self, url_or_id: str) -> dict:
        """Get comments from a Loom video.

        Note: The Loom API has changed and comments may not be directly available
        via the public GraphQL API. This method returns video info but comments
        may be empty.

        Args:
            url_or_id: Loom video URL or video ID

        Returns:
            Dict with video info and comments (if available)
        """
        video_id = self.extract_video_id(url_or_id)

        # Get video info (comments field is no longer available in public API)
        video_data = self._request(VIDEO_INFO_QUERY, {"videoId": video_id})
        video = video_data.get("getVideo")
        if not video or not video.get("name"):
            raise LoomNotFoundError(f"Video {video_id} not found or not accessible")

        # Note: Comments are no longer available via the public GraphQL API
        video["comments"] = []
        video["_comments_note"] = "Comments are no longer available via the Loom public API"

        return video


# =============================================================================
# CLI
# =============================================================================


def format_output(data: Any, fmt: str = "json") -> str:
    """Format output data.

    Args:
        data: Data to format
        fmt: Output format (json or text)

    Returns:
        Formatted string
    """
    if fmt == "json":
        return json.dumps(data, indent=2, default=str)
    elif fmt == "text":
        if isinstance(data, list):
            return "\n".join(str(item) for item in data)
        elif isinstance(data, dict):
            return "\n".join(f"{k}: {v}" for k, v in data.items())
        return str(data)
    return json.dumps(data, indent=2, default=str)


def format_timestamp(ms: Optional[int]) -> str:
    """Format milliseconds as MM:SS."""
    if ms is None:
        return ""
    seconds = ms // 1000
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def format_transcript_text(video: dict) -> str:
    """Format transcript as readable text."""
    lines = []

    # Video header
    lines.append(f"# {video.get('name', 'Untitled Video')}")
    owner = video.get("owner", {})
    if owner:
        lines.append(f"By: {owner.get('display_name', 'Unknown')}")
    lines.append("")

    # Transcript
    transcription = video.get("transcription")
    if not transcription:
        lines.append("(No transcript available)")
        return "\n".join(lines)

    sentences = transcription.get("sentences", [])
    if not sentences:
        lines.append("(No transcript sentences available)")
        return "\n".join(lines)

    lines.append("## Transcript")
    lines.append("")

    current_speaker = None
    for sentence in sentences:
        speaker = sentence.get("speaker_name", "Speaker")
        text = sentence.get("text", "")
        start_ts = sentence.get("start_ts")

        if speaker != current_speaker:
            lines.append("")
            timestamp = format_timestamp(start_ts)
            if timestamp:
                lines.append(f"**[{speaker}]** ({timestamp})")
            else:
                lines.append(f"**[{speaker}]**")
            current_speaker = speaker

        lines.append(text)

    return "\n".join(lines)


def format_comments_text(video: dict) -> str:
    """Format comments as readable text."""
    lines = []

    # Video header
    lines.append(f"# Comments: {video.get('name', 'Untitled Video')}")
    lines.append("")

    # Check for API limitation note
    if video.get("_comments_note"):
        lines.append(f"Note: {video['_comments_note']}")
        lines.append("")

    comments = video.get("comments", [])
    if not comments:
        lines.append("(No comments)")
        return "\n".join(lines)

    for i, comment in enumerate(comments, 1):
        author = comment.get("author", {})
        author_name = author.get("display_name", "Unknown")
        body = comment.get("body", "")
        timestamp_ms = comment.get("timestamp_ms")

        timestamp_str = ""
        if timestamp_ms:
            timestamp_str = f" at {format_timestamp(timestamp_ms)}"

        lines.append(f"## Comment {i} - {author_name}{timestamp_str}")
        lines.append(body)

        # Replies
        replies = comment.get("replies", [])
        for reply in replies:
            reply_author = reply.get("author", {})
            reply_author_name = reply_author.get("display_name", "Unknown")
            reply_body = reply.get("body", "")
            lines.append(f"  > **{reply_author_name}:** {reply_body}")

        lines.append("")

    return "\n".join(lines)


def cmd_transcript(args: argparse.Namespace) -> None:
    """Handle transcript command."""
    client = LoomClient()
    video = client.get_transcript(args.url)

    if args.output_format == "text":
        print(format_transcript_text(video))
    else:
        print(format_output(video, args.output_format))


def cmd_comments(args: argparse.Namespace) -> None:
    """Handle comments command."""
    client = LoomClient()
    video = client.get_comments(args.url)

    if args.output_format == "text":
        print(format_comments_text(video))
    else:
        print(format_output(video, args.output_format))


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Loom video transcript and comments CLI tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s transcript https://www.loom.com/share/abc123
  %(prog)s transcript abc123 --output-format text
  %(prog)s comments https://www.loom.com/share/abc123
        """,
    )
    parser.add_argument(
        "--output-format",
        "-o",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # transcript command
    transcript_parser = subparsers.add_parser(
        "transcript",
        help="Get transcript from a Loom video",
    )
    transcript_parser.add_argument(
        "url",
        help="Loom video URL or video ID",
    )
    transcript_parser.set_defaults(func=cmd_transcript)

    # comments command
    comments_parser = subparsers.add_parser(
        "comments",
        help="Get comments from a Loom video",
    )
    comments_parser.add_argument(
        "url",
        help="Loom video URL or video ID",
    )
    comments_parser.set_defaults(func=cmd_comments)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        args.func(args)
        return 0
    except LoomNotFoundError as e:
        print(f"Not found: {e}", file=sys.stderr)
        return 1
    except LoomNetworkError as e:
        print(f"Network error: {e}", file=sys.stderr)
        return 1
    except LoomError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

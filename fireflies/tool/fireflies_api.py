#!/usr/bin/env python3
"""Fireflies.ai API client and CLI tool.

Provides access to Fireflies.ai meeting transcription features:
- List and search meetings
- Get full transcripts with speaker identification
- Extract action items and summaries
- Speaker analytics and talk-time metrics
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Any, Optional

import requests

from .config import get_api_key


# =============================================================================
# Exceptions
# =============================================================================


class FirefliesError(Exception):
    """Base exception for Fireflies API errors."""
    pass


class FirefliesAuthError(FirefliesError):
    """Authentication failed - invalid or missing API key."""
    pass


class FirefliesRateLimitError(FirefliesError):
    """Rate limit exceeded."""
    pass


class FirefliesNotFoundError(FirefliesError):
    """Requested resource not found."""
    pass


# =============================================================================
# GraphQL Queries
# =============================================================================

QUERIES = {
    "list_transcripts": """
        query Transcripts($limit: Int, $skip: Int, $mine: Boolean, $host_email: String, $fromDate: Date, $toDate: Date) {
            transcripts(limit: $limit, skip: $skip, mine: $mine, host_email: $host_email, fromDate: $fromDate, toDate: $toDate) {
                id
                title
                date
                duration
                organizer_email
                participants
                transcript_url
            }
        }
    """,
    "get_transcript": """
        query Transcript($id: String!) {
            transcript(id: $id) {
                id
                title
                date
                duration
                organizer_email
                participants
                transcript_url
                summary {
                    action_items
                    keywords
                    overview
                    shorthand_bullet
                }
                sentences {
                    speaker_name
                    speaker_id
                    text
                    start_time
                    end_time
                }
            }
        }
    """,
    "get_transcript_basic": """
        query Transcript($id: String!) {
            transcript(id: $id) {
                id
                title
                date
                duration
                organizer_email
                participants
                transcript_url
                summary {
                    action_items
                    keywords
                    overview
                    shorthand_bullet
                }
            }
        }
    """,
    "search_transcripts": """
        query SearchTranscripts($keyword: String!, $limit: Int) {
            transcripts(limit: $limit) {
                id
                title
                date
                duration
                organizer_email
                participants
                sentences {
                    speaker_name
                    text
                }
            }
        }
    """,
    "get_user": """
        query User($id: String!) {
            user(id: $id) {
                user_id
                email
                name
                integrations
                minutes_consumed
                is_admin
            }
        }
    """,
    "get_current_user": """
        query CurrentUser {
            user {
                user_id
                email
                name
                integrations
                minutes_consumed
                is_admin
            }
        }
    """,
}


# =============================================================================
# Client
# =============================================================================


class FirefliesClient:
    """Client for Fireflies.ai GraphQL API."""

    API_ENDPOINT = "https://api.fireflies.ai/graphql"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize client with API key.

        Args:
            api_key: Fireflies API key. If not provided, reads from
                     FIREFLIES_API_KEY environment variable.
        """
        self.api_key = api_key or get_api_key("FIREFLIES_API_KEY")
        if not self.api_key:
            raise FirefliesAuthError(
                "No API key provided. Set FIREFLIES_API_KEY environment variable "
                "or pass api_key parameter."
            )

    def _request(self, query: str, variables: Optional[dict] = None) -> dict:
        """Make a GraphQL request to Fireflies API.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Response data dict

        Raises:
            FirefliesAuthError: If authentication fails
            FirefliesRateLimitError: If rate limit exceeded
            FirefliesNotFoundError: If resource not found
            FirefliesError: For other API errors
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = requests.post(
                self.API_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=30,
            )
        except requests.RequestException as e:
            raise FirefliesError(f"Request failed: {e}") from e

        if response.status_code == 401:
            raise FirefliesAuthError("Invalid API key")
        elif response.status_code == 429:
            raise FirefliesRateLimitError("Rate limit exceeded")
        elif response.status_code == 404:
            raise FirefliesNotFoundError("Resource not found")
        elif response.status_code >= 400:
            raise FirefliesError(f"API error {response.status_code}: {response.text}")

        data = response.json()

        if "errors" in data:
            errors = data["errors"]
            error_msg = "; ".join(e.get("message", str(e)) for e in errors)
            if "not found" in error_msg.lower():
                raise FirefliesNotFoundError(error_msg)
            raise FirefliesError(f"GraphQL errors: {error_msg}")

        return data.get("data", {})

    def list_meetings(
        self,
        limit: int = 20,
        skip: int = 0,
        mine: bool = False,
        host_email: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> list[dict]:
        """List meetings/transcripts.

        Args:
            limit: Maximum number of results (default 20)
            skip: Number of results to skip for pagination
            mine: Only show meetings where I am the organizer
            host_email: Filter by host email
            from_date: Filter meetings from this date (YYYY-MM-DD)
            to_date: Filter meetings to this date (YYYY-MM-DD)

        Returns:
            List of meeting dictionaries with id, title, date, duration, etc.
        """
        variables: dict[str, Any] = {"limit": limit, "skip": skip}

        if mine:
            variables["mine"] = True
        if host_email:
            variables["host_email"] = host_email
        if from_date:
            variables["fromDate"] = from_date
        if to_date:
            variables["toDate"] = to_date

        data = self._request(QUERIES["list_transcripts"], variables)
        return data.get("transcripts", [])

    def get_meeting(self, transcript_id: str, include_sentences: bool = False) -> dict:
        """Get a single meeting/transcript by ID.

        Args:
            transcript_id: The transcript ID
            include_sentences: Include full transcript sentences (can be large)

        Returns:
            Meeting dictionary with full details
        """
        query = QUERIES["get_transcript"] if include_sentences else QUERIES["get_transcript_basic"]
        data = self._request(query, {"id": transcript_id})
        transcript = data.get("transcript")
        if not transcript:
            raise FirefliesNotFoundError(f"Transcript {transcript_id} not found")
        return transcript

    def search_meetings(
        self,
        keyword: str,
        limit: int = 10,
    ) -> list[dict]:
        """Search meetings by keyword.

        Note: This is a client-side filter as Fireflies API doesn't have
        native search. Fetches meetings and filters by keyword in title
        and transcript content.

        Args:
            keyword: Search term
            limit: Maximum results to return

        Returns:
            List of matching meetings
        """
        # Fetch more than needed since we filter client-side
        data = self._request(QUERIES["search_transcripts"], {"limit": 100})
        transcripts = data.get("transcripts", [])

        keyword_lower = keyword.lower()
        results = []

        for t in transcripts:
            # Check title
            if keyword_lower in t.get("title", "").lower():
                results.append(t)
                continue

            # Check transcript sentences
            sentences = t.get("sentences", [])
            for s in sentences:
                if keyword_lower in s.get("text", "").lower():
                    results.append(t)
                    break

            if len(results) >= limit:
                break

        return results[:limit]

    def get_action_items(self, transcript_id: str) -> list[str]:
        """Get action items from a meeting.

        Args:
            transcript_id: The transcript ID

        Returns:
            List of action item strings
        """
        meeting = self.get_meeting(transcript_id, include_sentences=False)
        summary = meeting.get("summary", {}) or {}
        return summary.get("action_items", []) or []

    def get_summary(self, transcript_id: str) -> dict:
        """Get meeting summary.

        Args:
            transcript_id: The transcript ID

        Returns:
            Summary dict with overview, action_items, keywords, shorthand_bullet
        """
        meeting = self.get_meeting(transcript_id, include_sentences=False)
        return meeting.get("summary", {}) or {}

    def get_speaker_analytics(self, transcript_id: str) -> dict:
        """Get speaker analytics for a meeting.

        Calculates talk time and word count per speaker.

        Args:
            transcript_id: The transcript ID

        Returns:
            Dict with speaker stats: {speaker_name: {talk_time, word_count, sentences}}
        """
        meeting = self.get_meeting(transcript_id, include_sentences=True)
        sentences = meeting.get("sentences", []) or []

        stats: dict[str, dict] = {}

        for s in sentences:
            speaker = s.get("speaker_name", "Unknown")
            text = s.get("text", "")
            start = s.get("start_time", 0) or 0
            end = s.get("end_time", 0) or 0

            if speaker not in stats:
                stats[speaker] = {
                    "talk_time_seconds": 0,
                    "word_count": 0,
                    "sentence_count": 0,
                }

            stats[speaker]["talk_time_seconds"] += end - start
            stats[speaker]["word_count"] += len(text.split())
            stats[speaker]["sentence_count"] += 1

        # Calculate percentages
        total_time = sum(s["talk_time_seconds"] for s in stats.values())
        for speaker in stats:
            if total_time > 0:
                stats[speaker]["talk_time_percent"] = round(
                    stats[speaker]["talk_time_seconds"] / total_time * 100, 1
                )
            else:
                stats[speaker]["talk_time_percent"] = 0

        return stats

    def get_transcript_text(self, transcript_id: str) -> str:
        """Get full transcript as formatted text.

        Args:
            transcript_id: The transcript ID

        Returns:
            Formatted transcript string with speaker labels
        """
        meeting = self.get_meeting(transcript_id, include_sentences=True)
        sentences = meeting.get("sentences", []) or []

        if not sentences:
            return "(No transcript available)"

        lines = []
        current_speaker = None

        for s in sentences:
            speaker = s.get("speaker_name", "Unknown")
            text = s.get("text", "")

            if speaker != current_speaker:
                lines.append(f"\n[{speaker}]")
                current_speaker = speaker

            lines.append(text)

        return "\n".join(lines).strip()

    def get_user(self, user_id: Optional[str] = None) -> dict:
        """Get user information.

        Args:
            user_id: User ID. If not provided, returns current user.

        Returns:
            User dict with email, name, integrations, etc.
        """
        if user_id:
            data = self._request(QUERIES["get_user"], {"id": user_id})
        else:
            data = self._request(QUERIES["get_current_user"])

        user = data.get("user")
        if not user:
            raise FirefliesNotFoundError("User not found")
        return user


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


def format_meeting_list(meetings: list[dict]) -> str:
    """Format meeting list for display."""
    if not meetings:
        return "No meetings found"

    lines = []
    for m in meetings:
        date = m.get("date", "Unknown date")
        if isinstance(date, (int, float)):
            date = datetime.fromtimestamp(date / 1000).strftime("%Y-%m-%d %H:%M")
        duration = m.get("duration", 0) or 0
        duration_min = duration // 60 if duration else 0
        lines.append(
            f"- {m.get('title', 'Untitled')} ({date}, {duration_min}min)\n"
            f"  ID: {m.get('id')}\n"
            f"  Host: {m.get('organizer_email', 'Unknown')}"
        )
    return "\n\n".join(lines)


def cmd_meetings_list(args: argparse.Namespace) -> None:
    """Handle meetings list command."""
    client = FirefliesClient()
    meetings = client.list_meetings(
        limit=args.limit,
        skip=args.skip,
        mine=args.mine,
        host_email=args.host,
        from_date=args.from_date,
        to_date=args.to_date,
    )

    if args.output_format == "text":
        print(format_meeting_list(meetings))
    else:
        print(format_output(meetings, args.output_format))


def cmd_meetings_get(args: argparse.Namespace) -> None:
    """Handle meetings get command."""
    client = FirefliesClient()
    meeting = client.get_meeting(args.id, include_sentences=args.sentences)

    if args.output_format == "text":
        print(f"Title: {meeting.get('title', 'Untitled')}")
        print(f"Date: {meeting.get('date')}")
        print(f"Duration: {(meeting.get('duration', 0) or 0) // 60} minutes")
        print(f"Host: {meeting.get('organizer_email', 'Unknown')}")
        print(f"Participants: {', '.join(meeting.get('participants', []))}")
        if meeting.get("summary"):
            summary = meeting["summary"]
            if summary.get("overview"):
                print(f"\nOverview:\n{summary['overview']}")
    else:
        print(format_output(meeting, args.output_format))


def cmd_meetings_search(args: argparse.Namespace) -> None:
    """Handle meetings search command."""
    client = FirefliesClient()
    meetings = client.search_meetings(args.keyword, limit=args.limit)

    if args.output_format == "text":
        print(format_meeting_list(meetings))
    else:
        print(format_output(meetings, args.output_format))


def cmd_meetings_transcript(args: argparse.Namespace) -> None:
    """Handle meetings transcript command."""
    client = FirefliesClient()
    transcript = client.get_transcript_text(args.id)
    print(transcript)


def cmd_meetings_summary(args: argparse.Namespace) -> None:
    """Handle meetings summary command."""
    client = FirefliesClient()
    summary = client.get_summary(args.id)

    if args.output_format == "text":
        if summary.get("overview"):
            print("Overview:")
            print(summary["overview"])
            print()
        if summary.get("shorthand_bullet"):
            print("Key Points:")
            for bullet in summary["shorthand_bullet"]:
                print(f"  - {bullet}")
            print()
        if summary.get("keywords"):
            print(f"Keywords: {', '.join(summary['keywords'])}")
    else:
        print(format_output(summary, args.output_format))


def cmd_meetings_actions(args: argparse.Namespace) -> None:
    """Handle meetings actions command."""
    client = FirefliesClient()
    actions = client.get_action_items(args.id)

    if args.output_format == "text":
        if not actions:
            print("No action items found")
        else:
            print("Action Items:")
            for i, action in enumerate(actions, 1):
                print(f"  {i}. {action}")
    else:
        print(format_output(actions, args.output_format))


def cmd_meetings_speakers(args: argparse.Namespace) -> None:
    """Handle meetings speakers command."""
    client = FirefliesClient()
    stats = client.get_speaker_analytics(args.id)

    if args.output_format == "text":
        if not stats:
            print("No speaker data available")
        else:
            print("Speaker Analytics:")
            for speaker, data in sorted(
                stats.items(),
                key=lambda x: x[1]["talk_time_seconds"],
                reverse=True,
            ):
                print(f"\n  {speaker}:")
                print(f"    Talk time: {data['talk_time_seconds']:.0f}s ({data['talk_time_percent']}%)")
                print(f"    Words: {data['word_count']}")
                print(f"    Sentences: {data['sentence_count']}")
    else:
        print(format_output(stats, args.output_format))


def cmd_user(args: argparse.Namespace) -> None:
    """Handle user command."""
    client = FirefliesClient()
    user = client.get_user(args.id)

    if args.output_format == "text":
        print(f"Name: {user.get('name', 'Unknown')}")
        print(f"Email: {user.get('email', 'Unknown')}")
        print(f"User ID: {user.get('user_id')}")
        print(f"Admin: {user.get('is_admin', False)}")
        print(f"Minutes Consumed: {user.get('minutes_consumed', 0)}")
        if user.get("integrations"):
            print(f"Integrations: {', '.join(user['integrations'])}")
    else:
        print(format_output(user, args.output_format))


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Fireflies.ai API CLI tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output-format",
        "-o",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # meetings command group
    meetings_parser = subparsers.add_parser("meetings", help="Meeting operations")
    meetings_sub = meetings_parser.add_subparsers(dest="subcommand", help="Meeting subcommands")

    # meetings list
    list_parser = meetings_sub.add_parser("list", help="List meetings")
    list_parser.add_argument("--limit", "-l", type=int, default=20, help="Max results")
    list_parser.add_argument("--skip", "-s", type=int, default=0, help="Skip N results")
    list_parser.add_argument("--mine", "-m", action="store_true", help="Only my meetings")
    list_parser.add_argument("--host", help="Filter by host email")
    list_parser.add_argument("--from-date", help="From date (YYYY-MM-DD)")
    list_parser.add_argument("--to-date", help="To date (YYYY-MM-DD)")
    list_parser.set_defaults(func=cmd_meetings_list)

    # meetings get
    get_parser = meetings_sub.add_parser("get", help="Get meeting details")
    get_parser.add_argument("id", help="Meeting/transcript ID")
    get_parser.add_argument("--sentences", action="store_true", help="Include transcript sentences")
    get_parser.set_defaults(func=cmd_meetings_get)

    # meetings search
    search_parser = meetings_sub.add_parser("search", help="Search meetings")
    search_parser.add_argument("keyword", help="Search keyword")
    search_parser.add_argument("--limit", "-l", type=int, default=10, help="Max results")
    search_parser.set_defaults(func=cmd_meetings_search)

    # meetings transcript
    transcript_parser = meetings_sub.add_parser("transcript", help="Get full transcript text")
    transcript_parser.add_argument("id", help="Meeting/transcript ID")
    transcript_parser.set_defaults(func=cmd_meetings_transcript)

    # meetings summary
    summary_parser = meetings_sub.add_parser("summary", help="Get meeting summary")
    summary_parser.add_argument("id", help="Meeting/transcript ID")
    summary_parser.set_defaults(func=cmd_meetings_summary)

    # meetings actions
    actions_parser = meetings_sub.add_parser("actions", help="Get action items")
    actions_parser.add_argument("id", help="Meeting/transcript ID")
    actions_parser.set_defaults(func=cmd_meetings_actions)

    # meetings speakers
    speakers_parser = meetings_sub.add_parser("speakers", help="Get speaker analytics")
    speakers_parser.add_argument("id", help="Meeting/transcript ID")
    speakers_parser.set_defaults(func=cmd_meetings_speakers)

    # user command
    user_parser = subparsers.add_parser("user", help="Get user info")
    user_parser.add_argument("id", nargs="?", help="User ID (default: current user)")
    user_parser.set_defaults(func=cmd_user)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "meetings" and not args.subcommand:
        meetings_parser.print_help()
        return 1

    try:
        args.func(args)
        return 0
    except FirefliesAuthError as e:
        print(f"Authentication error: {e}", file=sys.stderr)
        return 1
    except FirefliesNotFoundError as e:
        print(f"Not found: {e}", file=sys.stderr)
        return 1
    except FirefliesRateLimitError as e:
        print(f"Rate limit exceeded: {e}", file=sys.stderr)
        return 1
    except FirefliesError as e:
        print(f"API error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""YouTube Transcript MCP Server - Get YouTube video transcripts for AI agents."""

from fastmcp import FastMCP
from typing import Optional

mcp = FastMCP("YouTube")
_client = None


def get_client():
    """Lazy initialization of YouTube client."""
    global _client
    if _client is None:
        from .youtube_api import YouTubeClient
        _client = YouTubeClient()
    return _client


@mcp.tool
def youtube_get_transcript(
    url_or_id: str,
    lang: Optional[str] = None,
) -> dict:
    """Get transcript text from a YouTube video.

    Args:
        url_or_id: YouTube video URL or video ID (supports youtube.com/watch, youtu.be, shorts, bare ID)
        lang: Language code (default: English, falls back to auto-generated)
    """
    return get_client().get_transcript(url_or_id, lang=lang)


@mcp.tool
def youtube_list_languages(url_or_id: str) -> dict:
    """List available transcript languages for a YouTube video.

    Args:
        url_or_id: YouTube video URL or video ID
    """
    return get_client().list_languages(url_or_id)


if __name__ == "__main__":
    mcp.run()

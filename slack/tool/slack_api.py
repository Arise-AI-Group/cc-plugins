#!/usr/bin/env python3
"""
Slack API Integration Script

Execution tool for managing Slack channels and messages via the Web API.
Supports: channel management, message retrieval, pins, canvases, and client onboarding.

Usage (CLI):
    python execution/slack_api.py channels list [--type public|private|all]
    python execution/slack_api.py channels create <name> [--private] [--description "..."]
    python execution/slack_api.py channels archive <channel_id>
    python execution/slack_api.py channels unarchive <channel_id>
    python execution/slack_api.py channels info <channel_id>
    python execution/slack_api.py channels set-topic <channel_id> "<topic>"
    python execution/slack_api.py channels set-purpose <channel_id> "<purpose>"

    python execution/slack_api.py messages get <channel_id> [--days 7] [--since DATE] [--until DATE]
    python execution/slack_api.py messages get-multi <channel_id1> <channel_id2> ... [--days 7]

    python execution/slack_api.py pins list <channel_id>
    python execution/slack_api.py pins add <channel_id> <message_ts>
    python execution/slack_api.py pins remove <channel_id> <message_ts>

    python execution/slack_api.py canvas create <channel_id> [--markdown "content"]
    python execution/slack_api.py canvas update <channel_id> --markdown-file <path>
    python execution/slack_api.py canvas get <channel_id>

    python execution/slack_api.py client setup <slug> [--display-name "Name"] [--canvas-template path] [--welcome-template path]

Usage (Module):
    from execution.slack_api import SlackClient
    client = SlackClient()
    channels = client.list_channels()
"""

import os
import sys
import json
import time
import re
import argparse
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .config import get_api_key

SLACK_BOT_TOKEN = get_api_key("SLACK_BOT_TOKEN")
SLACK_USER_TOKEN = get_api_key("SLACK_USER_TOKEN")


# --- Custom Exceptions ---

class SlackError(Exception):
    """Base exception for Slack API errors."""
    pass


class SlackAuthError(SlackError):
    """Authentication/token error."""
    pass


class SlackRateLimitError(SlackError):
    """Rate limit exceeded."""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after} seconds.")


class SlackNotFoundError(SlackError):
    """Channel/message not found."""
    pass


class SlackPermissionError(SlackError):
    """Insufficient permissions."""
    pass


class SlackClient:
    """Client for interacting with Slack Web API."""

    def __init__(self, bot_token: str = None, user_token: str = None):
        self.bot_token = bot_token or SLACK_BOT_TOKEN
        self.user_token = user_token or SLACK_USER_TOKEN

        if not self.bot_token:
            raise ValueError("SLACK_BOT_TOKEN not configured. Set it in .env file.")

        # Import slack_sdk here to allow module loading even without the package
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
            self._SlackApiError = SlackApiError
        except ImportError:
            raise ImportError("slack_sdk not installed. Run: pip install slack_sdk")

        self.client = WebClient(token=self.bot_token)
        self.user_client = WebClient(token=self.user_token) if self.user_token else None
        self._channel_cache: Dict[str, str] = {}  # name -> id cache

    def _handle_response(self, response) -> dict:
        """Handle Slack API response, raising appropriate exceptions."""
        if not response.get("ok"):
            error = response.get("error", "unknown_error")

            error_map = {
                "invalid_auth": SlackAuthError("Invalid token"),
                "token_revoked": SlackAuthError("Token has been revoked"),
                "not_authed": SlackAuthError("No authentication token provided"),
                "channel_not_found": SlackNotFoundError("Channel not found"),
                "message_not_found": SlackNotFoundError("Message not found"),
                "not_in_channel": SlackPermissionError("Bot not in channel"),
                "missing_scope": SlackPermissionError(f"Missing required scope: {response.get('needed', 'unknown')}"),
                "ratelimited": SlackRateLimitError(int(response.get("retry_after", 60))),
            }

            if error in error_map:
                raise error_map[error]
            raise SlackError(f"Slack API error: {error}")

        return response.data

    def _request_with_retry(self, method, max_retries: int = 3, **kwargs) -> dict:
        """Make request with automatic retry on rate limits."""
        for attempt in range(max_retries):
            try:
                response = method(**kwargs)
                return self._handle_response(response)
            except self._SlackApiError as e:
                if e.response.get("error") == "ratelimited":
                    retry_after = int(e.response.get("retry_after", 60))
                    print(f"Rate limited. Waiting {retry_after}s...", file=sys.stderr)
                    time.sleep(retry_after)
                else:
                    self._handle_response(e.response)

        raise SlackError("Max retries exceeded")

    # ==================== Channel Resolution ====================

    def resolve_channel(self, channel_name_or_id: str) -> str:
        """
        Resolve a channel name to its ID.
        Accepts either #channel-name or C01234567 format.

        Args:
            channel_name_or_id: Channel name (with or without #) or channel ID

        Returns:
            Channel ID (e.g., C01234567)
        """
        # If it looks like an ID, return as-is
        if channel_name_or_id.startswith(("C", "G")) and len(channel_name_or_id) >= 9:
            return channel_name_or_id

        # Strip # prefix if present
        name = channel_name_or_id.lstrip("#").lower()

        # Check cache first
        if name in self._channel_cache:
            return self._channel_cache[name]

        # Search for the channel
        channels = self.list_channels(types="public_channel,private_channel")
        for channel in channels:
            self._channel_cache[channel["name"].lower()] = channel["id"]
            if channel["name"].lower() == name:
                return channel["id"]

        raise SlackNotFoundError(f"Channel '{channel_name_or_id}' not found")

    # ==================== Channel Operations ====================

    def list_channels(
        self,
        types: str = "public_channel,private_channel",
        exclude_archived: bool = True,
        limit: int = 1000
    ) -> List[Dict]:
        """
        List all channels the bot has access to.

        Args:
            types: Comma-separated channel types (public_channel, private_channel)
            exclude_archived: Whether to exclude archived channels
            limit: Maximum channels to return

        Returns:
            List of channel objects with id, name, is_private, topic, purpose, etc.
        """
        all_channels = []
        cursor = None

        while len(all_channels) < limit:
            kwargs = {
                "types": types,
                "exclude_archived": exclude_archived,
                "limit": min(200, limit - len(all_channels))
            }
            if cursor:
                kwargs["cursor"] = cursor

            response = self._request_with_retry(self.client.conversations_list, **kwargs)
            all_channels.extend(response.get("channels", []))

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return all_channels

    def get_channel_info(self, channel: str) -> Dict:
        """
        Get detailed information about a channel.

        Args:
            channel: Channel ID or name (e.g., C01234567 or #general)

        Returns:
            Channel object with full details including canvas info
        """
        channel_id = self.resolve_channel(channel)
        response = self._request_with_retry(
            self.client.conversations_info,
            channel=channel_id,
            include_num_members=True
        )
        return response.get("channel", {})

    def create_channel(
        self,
        name: str,
        is_private: bool = False,
        description: str = None
    ) -> Dict:
        """
        Create a new channel.

        Args:
            name: Channel name (lowercase, no spaces, max 80 chars)
            is_private: Whether to create as private channel
            description: Optional channel description/purpose

        Returns:
            Created channel object with id and name
        """
        response = self._request_with_retry(
            self.client.conversations_create,
            name=name,
            is_private=is_private
        )
        channel = response.get("channel", {})

        # Set description/purpose if provided
        if description and channel.get("id"):
            self.set_channel_purpose(channel["id"], description)

        return channel

    def rename_channel(self, channel: str, new_name: str) -> Dict:
        """
        Rename a channel.

        Args:
            channel: Channel ID or current name
            new_name: New channel name (lowercase, no spaces, max 80 chars)

        Returns:
            Updated channel object
        """
        channel_id = self.resolve_channel(channel)
        response = self._request_with_retry(
            self.client.conversations_rename,
            channel=channel_id,
            name=new_name
        )
        # Clear cache since name changed
        self._channel_cache.clear()
        return response.get("channel", {})

    def join_channel(self, channel: str) -> Dict:
        """Join a public channel."""
        channel_id = self.resolve_channel(channel)
        response = self._request_with_retry(self.client.conversations_join, channel=channel_id)
        return response.get("channel", {})

    def join_all_channels(self) -> Dict[str, bool]:
        """Join all public channels the bot is not a member of."""
        channels = self.list_channels(types="public_channel")
        results = {}
        for ch in channels:
            if not ch.get("is_member"):
                name = ch.get("name", ch.get("id"))
                try:
                    self.join_channel(ch["id"])
                    results[name] = True
                except Exception as e:
                    results[name] = False
        return results

    def archive_channel(self, channel: str) -> bool:
        """Archive a channel."""
        channel_id = self.resolve_channel(channel)
        self._request_with_retry(self.client.conversations_archive, channel=channel_id)
        return True

    def unarchive_channel(self, channel: str) -> bool:
        """Unarchive a channel."""
        channel_id = self.resolve_channel(channel)
        self._request_with_retry(self.client.conversations_unarchive, channel=channel_id)
        return True

    def set_channel_topic(self, channel: str, topic: str) -> str:
        """
        Set the channel topic (short description shown in header).

        Args:
            channel: Channel ID or name
            topic: New topic text (max 250 chars)

        Returns:
            The updated topic string
        """
        channel_id = self.resolve_channel(channel)
        response = self._request_with_retry(
            self.client.conversations_setTopic,
            channel=channel_id,
            topic=topic
        )
        return response.get("topic", topic)

    def set_channel_purpose(self, channel: str, purpose: str) -> str:
        """
        Set the channel purpose (longer description).

        Args:
            channel: Channel ID or name
            purpose: New purpose text (max 250 chars)

        Returns:
            The updated purpose string
        """
        channel_id = self.resolve_channel(channel)
        response = self._request_with_retry(
            self.client.conversations_setPurpose,
            channel=channel_id,
            purpose=purpose
        )
        return response.get("purpose", purpose)

    # ==================== Message Operations ====================

    def get_messages(
        self,
        channel: str,
        oldest: float = None,
        latest: float = None,
        limit: int = 100,
        include_all_metadata: bool = False
    ) -> List[Dict]:
        """
        Retrieve messages from a channel with optional time filtering.

        Args:
            channel: Channel ID or name
            oldest: Unix timestamp - only messages after this time
            latest: Unix timestamp - only messages before this time
            limit: Max messages to retrieve (will paginate if more)
            include_all_metadata: Include all message metadata

        Returns:
            List of message objects sorted oldest to newest
        """
        channel_id = self.resolve_channel(channel)
        all_messages = []
        cursor = None

        while len(all_messages) < limit:
            kwargs = {
                "channel": channel_id,
                "limit": min(200, limit - len(all_messages)),
                "include_all_metadata": include_all_metadata
            }
            if oldest:
                kwargs["oldest"] = str(oldest)
            if latest:
                kwargs["latest"] = str(latest)
            if cursor:
                kwargs["cursor"] = cursor

            response = self._request_with_retry(self.client.conversations_history, **kwargs)
            messages = response.get("messages", [])
            all_messages.extend(messages)

            if not response.get("has_more"):
                break
            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        # Sort oldest to newest (API returns newest first)
        all_messages.reverse()
        return all_messages

    def get_messages_by_date_range(
        self,
        channel: str,
        start_date: str,
        end_date: str = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Convenience method using ISO date strings.

        Args:
            channel: Channel ID or name
            start_date: ISO date string (e.g., "2024-01-01" or "2024-01-01T09:00:00")
            end_date: ISO date string (defaults to now)
            limit: Max messages to return

        Returns:
            List of messages in the date range
        """
        oldest = self.parse_date_to_timestamp(start_date)
        latest = self.parse_date_to_timestamp(end_date) if end_date else None

        return self.get_messages(channel, oldest=oldest, latest=latest, limit=limit)

    def get_messages_multi(
        self,
        channels: List[str],
        oldest: float = None,
        latest: float = None,
        limit_per_channel: int = 100
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve messages from multiple channels.

        Args:
            channels: List of channel IDs or names
            oldest: Unix timestamp filter
            latest: Unix timestamp filter
            limit_per_channel: Max messages per channel

        Returns:
            Dict mapping channel_id -> list of messages
        """
        result = {}
        for channel in channels:
            try:
                channel_id = self.resolve_channel(channel)
                result[channel_id] = self.get_messages(
                    channel_id,
                    oldest=oldest,
                    latest=latest,
                    limit=limit_per_channel
                )
            except SlackError as e:
                print(f"Warning: Could not fetch messages from {channel}: {e}", file=sys.stderr)
                result[channel] = []

        return result

    # ==================== Pin Operations ====================

    def list_pins(self, channel: str) -> List[Dict]:
        """List all pinned items in a channel."""
        channel_id = self.resolve_channel(channel)
        response = self._request_with_retry(self.client.pins_list, channel=channel_id)
        return response.get("items", [])

    def add_pin(self, channel: str, message_ts: str) -> bool:
        """
        Pin a message to a channel.

        Args:
            channel: Channel ID or name
            message_ts: Timestamp of the message to pin

        Returns:
            True if successful
        """
        channel_id = self.resolve_channel(channel)
        self._request_with_retry(
            self.client.pins_add,
            channel=channel_id,
            timestamp=message_ts
        )
        return True

    def remove_pin(self, channel: str, message_ts: str) -> bool:
        """Remove a pin from a message."""
        channel_id = self.resolve_channel(channel)
        self._request_with_retry(
            self.client.pins_remove,
            channel=channel_id,
            timestamp=message_ts
        )
        return True

    # ==================== Message Deletion ====================

    def delete_message(self, channel: str, message_ts: str, use_user_token: bool = False) -> bool:
        """
        Delete a message from a channel.

        Args:
            channel: Channel ID or name
            message_ts: Timestamp of the message to delete
            use_user_token: If True, use user token (can delete any message).
                           If False, use bot token (can only delete bot's own messages).

        Returns:
            True if successful
        """
        channel_id = self.resolve_channel(channel)

        if use_user_token:
            if not self.user_client:
                raise SlackPermissionError("User token required to delete other users' messages. Set SLACK_USER_TOKEN in .env")
            client = self.user_client
        else:
            client = self.client

        self._request_with_retry(
            client.chat_delete,
            channel=channel_id,
            ts=message_ts
        )
        return True

    def clear_channel_messages(self, channel: str, use_user_token: bool = False) -> int:
        """
        Delete messages from a channel.

        Args:
            channel: Channel ID or name
            use_user_token: If True, delete ALL messages (requires user token).
                           If False, delete only bot's own messages.

        Returns:
            Number of messages deleted
        """
        channel_id = self.resolve_channel(channel)

        # Get all messages in the channel
        messages = self.get_messages(channel_id, limit=100)

        if use_user_token:
            # Delete ALL messages with user token
            if not self.user_client:
                raise SlackPermissionError("User token required. Set SLACK_USER_TOKEN in .env")

            deleted_count = 0
            for msg in messages:
                try:
                    self.delete_message(channel_id, msg["ts"], use_user_token=True)
                    deleted_count += 1
                except SlackError:
                    # Some system messages may still fail
                    pass
            return deleted_count
        else:
            # Only delete bot's own messages
            auth_response = self._request_with_retry(self.client.auth_test)
            bot_user_id = auth_response.get("user_id")

            deleted_count = 0
            for msg in messages:
                if msg.get("user") == bot_user_id or msg.get("bot_id"):
                    try:
                        self.delete_message(channel_id, msg["ts"])
                        deleted_count += 1
                    except SlackError:
                        pass

            return deleted_count

    # ==================== Canvas Operations ====================

    def create_channel_canvas(
        self,
        channel: str,
        markdown_content: str = None
    ) -> Dict:
        """
        Create a channel canvas (also called the channel's "first post" or description doc).

        Args:
            channel: Channel ID or name
            markdown_content: Optional initial content in markdown

        Returns:
            Canvas info including canvas_id
        """
        channel_id = self.resolve_channel(channel)

        kwargs = {"channel_id": channel_id}
        if markdown_content:
            kwargs["document_content"] = {"type": "markdown", "markdown": markdown_content}

        response = self._request_with_retry(
            self.client.conversations_canvases_create,
            **kwargs
        )
        return response

    def update_channel_canvas(
        self,
        channel: str,
        markdown_content: str
    ) -> bool:
        """
        Update the channel canvas content.

        Args:
            channel: Channel ID or name
            markdown_content: New content in markdown format

        Returns:
            True if successful
        """
        # First get the canvas ID from channel info
        channel_info = self.get_channel_info(channel)
        canvas_id = channel_info.get("properties", {}).get("canvas", {}).get("file_id")

        if not canvas_id:
            raise SlackNotFoundError(f"No canvas found for channel {channel}. Create one first.")

        # Update the canvas
        self._request_with_retry(
            self.client.canvases_edit,
            canvas_id=canvas_id,
            changes=[{
                "operation": "replace",
                "document_content": {"type": "markdown", "markdown": markdown_content}
            }]
        )
        return True

    def get_channel_canvas(self, channel: str) -> Dict:
        """Get the channel canvas content and metadata."""
        channel_info = self.get_channel_info(channel)
        canvas_id = channel_info.get("properties", {}).get("canvas", {}).get("file_id")

        if not canvas_id:
            return {"error": "No canvas found for this channel"}

        # Get canvas sections/content
        response = self._request_with_retry(
            self.client.canvases_sections_lookup,
            canvas_id=canvas_id,
            criteria={"contains_text": ""}  # Get all sections
        )

        return {
            "canvas_id": canvas_id,
            "sections": response.get("sections", [])
        }

    # ==================== User Group Operations ====================

    def list_usergroups(self, include_disabled: bool = False) -> List[Dict]:
        """
        List all user groups in the workspace.

        Args:
            include_disabled: Include disabled user groups

        Returns:
            List of user group objects
        """
        response = self._request_with_retry(
            self.client.usergroups_list,
            include_disabled=include_disabled,
            include_users=True
        )
        return response.get("usergroups", [])

    def create_usergroup(
        self,
        name: str,
        handle: str = None,
        description: str = None,
        channels: List[str] = None,
        users: List[str] = None,
        enable_section: bool = True
    ) -> Dict:
        """
        Create a user group with optional sidebar section.

        Args:
            name: Display name for the group (e.g., "Client - Acme")
            handle: Mention handle without @ (e.g., "client-acme"). Defaults to slugified name.
            description: Group description
            channels: List of default channel IDs/names for group members
            users: List of user IDs to add to the group
            enable_section: If True, creates a sidebar section for group channels

        Returns:
            Created user group object
        """
        # Generate handle from name if not provided
        if not handle:
            handle = name.lower().replace(" ", "-").replace("_", "-")

        # Resolve channel names to IDs
        channel_ids = []
        if channels:
            for ch in channels:
                channel_ids.append(self.resolve_channel(ch))

        kwargs = {
            "name": name,
            "handle": handle,
        }

        if description:
            kwargs["description"] = description
        if channel_ids:
            kwargs["channels"] = ",".join(channel_ids)

        response = self._request_with_retry(
            self.client.usergroups_create,
            **kwargs
        )
        usergroup = response.get("usergroup", {})

        # Add users to the group if specified
        if users and usergroup.get("id"):
            self.update_usergroup_members(usergroup["id"], users)

        # Note: enable_section is set via Slack admin UI or during group creation
        # The API doesn't directly expose this, but channels become default for members

        return usergroup

    def update_usergroup(
        self,
        usergroup_id: str,
        name: str = None,
        handle: str = None,
        description: str = None,
        channels: List[str] = None
    ) -> Dict:
        """
        Update a user group's properties.

        Args:
            usergroup_id: The user group ID
            name: New display name
            handle: New mention handle
            description: New description
            channels: New list of default channel IDs/names

        Returns:
            Updated user group object
        """
        kwargs = {"usergroup": usergroup_id}

        if name:
            kwargs["name"] = name
        if handle:
            kwargs["handle"] = handle
        if description:
            kwargs["description"] = description
        if channels:
            channel_ids = [self.resolve_channel(ch) for ch in channels]
            kwargs["channels"] = ",".join(channel_ids)

        response = self._request_with_retry(
            self.client.usergroups_update,
            **kwargs
        )
        return response.get("usergroup", {})

    def update_usergroup_members(self, usergroup_id: str, user_ids: List[str]) -> Dict:
        """
        Set the members of a user group (replaces existing members).

        Args:
            usergroup_id: The user group ID
            user_ids: List of user IDs to set as members

        Returns:
            Updated user group object
        """
        response = self._request_with_retry(
            self.client.usergroups_users_update,
            usergroup=usergroup_id,
            users=",".join(user_ids)
        )
        return response.get("usergroup", {})

    def get_usergroup_members(self, usergroup_id: str) -> List[str]:
        """
        Get the members of a user group.

        Args:
            usergroup_id: The user group ID

        Returns:
            List of user IDs
        """
        response = self._request_with_retry(
            self.client.usergroups_users_list,
            usergroup=usergroup_id
        )
        return response.get("users", [])

    def disable_usergroup(self, usergroup_id: str) -> Dict:
        """Disable (archive) a user group."""
        response = self._request_with_retry(
            self.client.usergroups_disable,
            usergroup=usergroup_id
        )
        return response.get("usergroup", {})

    def enable_usergroup(self, usergroup_id: str) -> Dict:
        """Re-enable a disabled user group."""
        response = self._request_with_retry(
            self.client.usergroups_enable,
            usergroup=usergroup_id
        )
        return response.get("usergroup", {})

    # ==================== User Operations ====================

    def invite_users(self, channel: str, user_ids: List[str]) -> Dict:
        """
        Invite users to a channel.

        Args:
            channel: Channel ID or name
            user_ids: List of user IDs to invite

        Returns:
            Response with channel info
        """
        channel_id = self.resolve_channel(channel)
        response = self._request_with_retry(
            self.client.conversations_invite,
            channel=channel_id,
            users=",".join(user_ids)
        )
        return response.get("channel", {})

    def list_users(self, limit: int = 200) -> List[Dict]:
        """
        List all users in the workspace.

        Args:
            limit: Max users to return

        Returns:
            List of user objects
        """
        all_users = []
        cursor = None

        while len(all_users) < limit:
            kwargs = {"limit": min(200, limit - len(all_users))}
            if cursor:
                kwargs["cursor"] = cursor

            response = self._request_with_retry(self.client.users_list, **kwargs)
            users = response.get("members", [])
            # Filter out bots and deactivated users
            real_users = [u for u in users if not u.get("is_bot") and not u.get("deleted")]
            all_users.extend(real_users)

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return all_users

    def get_user_info(self, user_id: str) -> Dict:
        """Get user details for attribution in summaries."""
        response = self._request_with_retry(self.client.users_info, user=user_id)
        return response.get("user", {})

    def get_user_name(self, user_id: str) -> str:
        """Get display name for a user ID."""
        try:
            user = self.get_user_info(user_id)
            return user.get("real_name") or user.get("name") or user_id
        except SlackError:
            return user_id

    # ==================== Message Posting ====================

    def post_message(
        self,
        channel: str,
        text: str,
        blocks: List[Dict] = None,
        thread_ts: str = None
    ) -> Dict:
        """
        Post a message to a channel.

        Args:
            channel: Channel ID or name
            text: Message text (also used as fallback for blocks)
            blocks: Optional Block Kit blocks for rich formatting
            thread_ts: Optional thread timestamp to reply in thread

        Returns:
            Message object with ts (timestamp) for pinning/threading
        """
        channel_id = self.resolve_channel(channel)
        kwargs = {
            "channel": channel_id,
            "text": text
        }
        if blocks:
            kwargs["blocks"] = blocks
        if thread_ts:
            kwargs["thread_ts"] = thread_ts

        response = self._request_with_retry(
            self.client.chat_postMessage,
            **kwargs
        )
        return response.get("message", {})

    # ==================== Client Setup ====================

    def setup_client(
        self,
        client_slug: str,
        display_name: str = None,
        canvas_template_path: str = None,
        welcome_template_path: str = None,
        notification_channel: str = "#new-clients"
    ) -> Dict:
        """
        Full client channel setup - creates channels, clears messages, adds canvas, welcome message, and notifies team.

        Args:
            client_slug: Short name for channel (e.g., "acme" -> #acme, #acme-internal)
            display_name: Human-readable client name (defaults to titleized slug)
            canvas_template_path: Path to markdown template for canvas
            welcome_template_path: Path to markdown template for welcome message
            notification_channel: Channel to post notification about new client (default: #new-clients, None to skip)

        Returns:
            Dict with created channel IDs and status of each step
        """
        import os
        from datetime import datetime

        display_name = display_name or client_slug.replace("-", " ").title()
        today = datetime.now().strftime("%Y-%m-%d")

        # Template variables
        template_vars = {
            "client_name": client_slug,
            "display_name": display_name,
            "date": today
        }

        result = {
            "client_slug": client_slug,
            "display_name": display_name,
            "client_channel": None,
            "internal_channel": None,
            "steps": []
        }

        def log_step(success: bool, message: str):
            status = "✓" if success else "✗"
            print(f"  {status} {message}", file=sys.stderr)
            result["steps"].append({"success": success, "message": message})

        print(f"Setting up client: {display_name} ({client_slug})", file=sys.stderr)

        # 1. Create public client channel (guests will be invited here)
        try:
            client_channel = self.create_channel(
                client_slug,
                is_private=False,
                description=f"Client communications with {display_name}. Guests welcome."
            )
            result["client_channel"] = client_channel.get("id")
            log_step(True, f"Created #{client_slug} ({client_channel.get('id')})")
        except SlackError as e:
            log_step(False, f"Failed to create #{client_slug}: {e}")
            return result

        # 2. Create public internal channel (team only, no guests)
        try:
            internal_channel = self.create_channel(
                f"{client_slug}-internal",
                is_private=False,
                description=f"Internal discussions about {display_name}. No clients."
            )
            result["internal_channel"] = internal_channel.get("id")
            log_step(True, f"Created #{client_slug}-internal ({internal_channel.get('id')})")
        except SlackError as e:
            log_step(False, f"Failed to create #{client_slug}-internal: {e}")

        # 3. Clear all messages from both channels (removes system messages like "joined", "set description")
        # Uses user token if available for full message deletion, otherwise only bot messages
        use_user_token = self.user_client is not None
        try:
            deleted_client = self.clear_channel_messages(result["client_channel"], use_user_token=use_user_token) if result["client_channel"] else 0
            deleted_internal = self.clear_channel_messages(result["internal_channel"], use_user_token=use_user_token) if result["internal_channel"] else 0
            total_deleted = deleted_client + deleted_internal
            if total_deleted > 0:
                mode = "all messages" if use_user_token else "bot messages only"
                log_step(True, f"Cleared {total_deleted} message(s) from channels ({mode})")
            else:
                log_step(True, "No messages to clear")
        except SlackError as e:
            log_step(False, f"Failed to clear messages: {e}")

        # 4. Create canvas from template (only in client channel)
        if canvas_template_path and os.path.exists(canvas_template_path):
            try:
                with open(canvas_template_path, 'r') as f:
                    canvas_content = f.read()
                # Apply template variables
                for key, value in template_vars.items():
                    canvas_content = canvas_content.replace(f"{{{key}}}", value)

                self.create_channel_canvas(result["client_channel"], canvas_content)
                log_step(True, f"Created canvas in #{client_slug}")
            except SlackError as e:
                log_step(False, f"Failed to create canvas: {e}")
            except Exception as e:
                log_step(False, f"Failed to read canvas template: {e}")
        elif canvas_template_path:
            log_step(False, f"Canvas template not found: {canvas_template_path}")

        # 5. Post welcome message (only in client channel)
        if welcome_template_path and os.path.exists(welcome_template_path):
            try:
                with open(welcome_template_path, 'r') as f:
                    welcome_content = f.read()
                # Apply template variables
                for key, value in template_vars.items():
                    welcome_content = welcome_content.replace(f"{{{key}}}", value)

                message = self.post_message(result["client_channel"], welcome_content)
                # Pin the welcome message
                if message.get("ts"):
                    self.add_pin(result["client_channel"], message["ts"])
                log_step(True, "Posted and pinned welcome message")
            except SlackError as e:
                log_step(False, f"Failed to post welcome message: {e}")
            except Exception as e:
                log_step(False, f"Failed to read welcome template: {e}")
        elif welcome_template_path:
            log_step(False, f"Welcome template not found: {welcome_template_path}")

        # 6. Post notification to team channel
        if notification_channel:
            try:
                notification_msg = f"🆕 *New client channels created:*\n• <#{result['client_channel']}> - Client communications with {display_name}\n• <#{result['internal_channel']}> - Internal team discussions"
                self.post_message(notification_channel, notification_msg)
                log_step(True, f"Posted notification to {notification_channel}")
            except SlackError as e:
                log_step(False, f"Failed to post notification to {notification_channel}: {e}")

        # Summary
        print(f"\nClient setup complete!", file=sys.stderr)
        print(f"Channels: #{client_slug}, #{client_slug}-internal", file=sys.stderr)
        print(f"Next step: Invite client guests to #{client_slug}", file=sys.stderr)

        return result

    # ==================== Huddle Operations ====================

    def find_huddles(
        self,
        channel: str,
        days: int = None,
        hours: int = None,
        since: str = None,
        until: str = None,
        limit: int = 500
    ) -> List[Dict]:
        """
        Find all huddles in a channel with full metadata preserved.

        Args:
            channel: Channel ID or name
            days: Get huddles from last N days
            hours: Get huddles from last N hours
            since: Start date (ISO format: YYYY-MM-DD)
            until: End date (ISO format: YYYY-MM-DD)
            limit: Max messages to scan (default 500)

        Returns:
            List of huddle objects with full metadata including:
            - huddle: Full room metadata (id, participants, timestamps, recording info)
            - notes: Huddle notes canvas metadata (if available)
            - transcript: Transcript file metadata (if available)
            - message: Original message metadata (ts, thread_ts, replies, etc.)
            - channel: Channel info
        """
        channel_id = self.resolve_channel(channel)

        # Calculate time range
        oldest = None
        latest = None
        if days:
            oldest = (datetime.now() - timedelta(days=days)).timestamp()
        elif hours:
            oldest = (datetime.now() - timedelta(hours=hours)).timestamp()
        elif since:
            oldest = self.parse_date_to_timestamp(since)
        if until:
            latest = self.parse_date_to_timestamp(until)

        # Get messages and filter for huddles
        messages = self.get_messages(
            channel_id,
            oldest=oldest,
            latest=latest,
            limit=limit,
            include_all_metadata=True
        )

        huddles = []
        for msg in messages:
            # Check if this is a huddle message
            if msg.get("subtype") != "huddle_thread":
                continue

            room = msg.get("room", {})
            if not room or room.get("call_family") != "huddle":
                continue

            # Extract huddle notes canvas from files
            notes_canvas = None
            transcript_file = None
            other_files = []

            for file in msg.get("files", []):
                if file.get("is_huddle_canvas"):
                    notes_canvas = file
                elif file.get("id") == room.get("transcript_file_id"):
                    transcript_file = file
                else:
                    other_files.append(file)

            # Build comprehensive huddle object
            huddle_data = {
                # Core identifiers
                "id": room.get("id"),
                "channel_id": channel_id,
                "channel": msg.get("channel"),

                # Timestamps
                "date_start": room.get("date_start"),
                "date_end": room.get("date_end"),
                "date_start_formatted": self.format_timestamp(room.get("date_start")) if room.get("date_start") else None,
                "date_end_formatted": self.format_timestamp(room.get("date_end")) if room.get("date_end") else None,
                "duration_seconds": (room.get("date_end", 0) - room.get("date_start", 0)) if room.get("date_end") and room.get("date_start") else None,

                # Participants
                "created_by": room.get("created_by"),
                "participant_history": room.get("participant_history", []),
                "participant_count": len(room.get("participant_history", [])),
                "participants_events": room.get("participants_events", {}),

                # Links
                "huddle_link": room.get("huddle_link"),
                "permalink": msg.get("permalink"),

                # Recording & Transcript
                "recording": room.get("recording", {}),
                "has_transcript": room.get("recording", {}).get("transcript", False),
                "has_summary": room.get("recording", {}).get("summary", False),
                "summary_status": room.get("recording", {}).get("summary_status"),
                "transcript_file_id": room.get("transcript_file_id"),
                "recording_user": room.get("recording", {}).get("recording_user"),

                # Notes canvas (full metadata)
                "notes": {
                    "file_id": notes_canvas.get("id") if notes_canvas else None,
                    "title": notes_canvas.get("title") if notes_canvas else None,
                    "permalink": notes_canvas.get("permalink") if notes_canvas else None,
                    "url_private": notes_canvas.get("url_private") if notes_canvas else None,
                    "size": notes_canvas.get("size") if notes_canvas else None,
                    "created": notes_canvas.get("created") if notes_canvas else None,
                    "updated": notes_canvas.get("updated") if notes_canvas else None,
                    "huddle_summary_id": notes_canvas.get("huddle_summary_id") if notes_canvas else None,
                    "huddle_transcript_file_id": notes_canvas.get("huddle_transcript_file_id") if notes_canvas else None,
                    "quip_thread_id": notes_canvas.get("quip_thread_id") if notes_canvas else None,
                    "full_metadata": notes_canvas  # Preserve complete file metadata
                } if notes_canvas else None,

                # Transcript file (full metadata)
                "transcript": {
                    "file_id": transcript_file.get("id") if transcript_file else room.get("transcript_file_id"),
                    "full_metadata": transcript_file
                } if transcript_file or room.get("transcript_file_id") else None,

                # Other attached files
                "attached_files": other_files,
                "attached_file_ids": room.get("attached_file_ids", []),

                # Message context
                "message": {
                    "ts": msg.get("ts"),
                    "thread_ts": msg.get("thread_ts"),
                    "reply_count": msg.get("reply_count", 0),
                    "reply_users": msg.get("reply_users", []),
                    "latest_reply": msg.get("latest_reply"),
                    "edited": msg.get("edited"),
                    "team": msg.get("team")
                },

                # Full room metadata (preserve everything)
                "room_metadata": room,

                # Status flags
                "has_ended": room.get("has_ended", False),
                "is_scheduled": room.get("is_scheduled", False),
                "was_missed": room.get("was_missed", False),
                "was_rejected": room.get("was_rejected", False),

                # Additional metadata
                "locale": room.get("locale"),
                "background_id": room.get("background_id"),
                "external_unique_id": room.get("external_unique_id"),
                "media_backend_type": room.get("media_backend_type")
            }

            huddles.append(huddle_data)

        return huddles

    def find_huddles_multi(
        self,
        channels: List[str] = None,
        days: int = None,
        hours: int = None,
        since: str = None,
        until: str = None,
        limit_per_channel: int = 500
    ) -> Dict[str, List[Dict]]:
        """
        Find huddles across multiple channels.

        Args:
            channels: List of channel IDs/names (None = all channels)
            days: Get huddles from last N days
            hours: Get huddles from last N hours
            since: Start date (ISO format)
            until: End date (ISO format)
            limit_per_channel: Max messages to scan per channel

        Returns:
            Dict mapping channel_id -> list of huddle objects
        """
        if channels is None:
            # Get all channels
            all_channels = self.list_channels()
            channels = [ch["id"] for ch in all_channels]

        result = {}
        for channel in channels:
            try:
                channel_id = self.resolve_channel(channel)
                huddles = self.find_huddles(
                    channel_id,
                    days=days,
                    hours=hours,
                    since=since,
                    until=until,
                    limit=limit_per_channel
                )
                if huddles:  # Only include channels with huddles
                    result[channel_id] = huddles
            except SlackError as e:
                print(f"Warning: Could not fetch huddles from {channel}: {e}", file=sys.stderr)

        return result

    def get_huddle_notes_content(self, notes_file_id: str) -> Dict:
        """
        Retrieve the actual content of a huddle notes canvas.

        Args:
            notes_file_id: The file ID of the huddle notes canvas

        Returns:
            Dict with canvas content (html and text) and metadata
        """
        import urllib.request
        import re

        # Get file info to get download URL
        file_info = self._request_with_retry(
            self.client.files_info,
            file=notes_file_id
        )

        file_data = file_info.get("file", {})
        download_url = file_data.get("url_private_download")

        if not download_url:
            return {
                "canvas_id": notes_file_id,
                "html": "",
                "text": "",
                "error": "No download URL available"
            }

        # Download the canvas content
        token = self.client.token
        req = urllib.request.Request(
            download_url,
            headers={"Authorization": f"Bearer {token}"}
        )

        try:
            with urllib.request.urlopen(req) as resp:
                html_content = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            return {
                "canvas_id": notes_file_id,
                "html": "",
                "text": "",
                "error": str(e)
            }

        # Convert HTML to Markdown (preserve structure)
        text_content = self._html_to_markdown(html_content)

        return {
            "canvas_id": notes_file_id,
            "html": html_content,
            "text": text_content,
            "title": file_data.get("title", "")
        }

    def get_transcript_content(self, transcript_file_id: str, use_user_token: bool = True) -> Dict:
        """
        Download raw huddle transcript file content (VTT or similar format).

        Args:
            transcript_file_id: The huddle_transcript_file_id from huddle notes,
                               or transcript.file_id from find_huddles()
            use_user_token: If True (default), use user token for download which has
                           broader file access permissions. Falls back to bot token.

        Returns:
            Dict with transcript content and metadata including:
            - file_id: The file ID
            - filetype: File type (e.g., 'vtt')
            - name: File name
            - content: Raw transcript text content
            - title: File title
        """
        import urllib.request

        # Get file info to get download URL (bot token works for this)
        file_info = self._request_with_retry(
            self.client.files_info,
            file=transcript_file_id
        )

        file_data = file_info.get("file", {})
        download_url = file_data.get("url_private_download")

        if not download_url:
            return {
                "file_id": transcript_file_id,
                "error": "No download URL available - file may require different permissions"
            }

        # Use user token for download if available (has broader file access)
        # Bot tokens often can't download huddle transcript files
        if use_user_token and self.user_client:
            token = self.user_client.token
        else:
            token = self.client.token
            if use_user_token and not self.user_client:
                print("Warning: User token not configured. Trying bot token (may fail for transcript files).", file=sys.stderr)

        req = urllib.request.Request(
            download_url,
            headers={"Authorization": f"Bearer {token}"}
        )

        try:
            with urllib.request.urlopen(req) as resp:
                content = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            return {
                "file_id": transcript_file_id,
                "error": str(e)
            }

        # Check if we got HTML (login redirect) instead of actual content
        if content.strip().startswith("<!DOCTYPE html") or content.strip().startswith("<html"):
            # huddle_transcript files are protected by Slack and don't support API download
            filetype = file_data.get("filetype")
            if filetype == "huddle_transcript":
                error_msg = (
                    "Slack's huddle_transcript files don't support API download (requires browser session). "
                    "Use 'huddles notes <notes_file_id>' instead to get the AI-generated summary, "
                    "which includes key points, action items, and timestamped references."
                )
            else:
                error_msg = "Got HTML redirect instead of content. Token may lack required scopes."
            return {
                "file_id": transcript_file_id,
                "filetype": filetype,
                "name": file_data.get("name"),
                "error": error_msg
            }

        return {
            "file_id": transcript_file_id,
            "filetype": file_data.get("filetype"),
            "name": file_data.get("name"),
            "title": file_data.get("title", ""),
            "size": file_data.get("size"),
            "content": content
        }

    # ==================== Helper Methods ====================

    # Common Slack emoji codes to Unicode mapping
    EMOJI_MAP = {
        ":headphones:": "\U0001F3A7",
        ":microphone:": "\U0001F3A4",
        ":speech_balloon:": "\U0001F4AC",
        ":memo:": "\U0001F4DD",
        ":clipboard:": "\U0001F4CB",
        ":pushpin:": "\U0001F4CC",
        ":round_pushpin:": "\U0001F4CD",
        ":star:": "\U00002B50",
        ":star2:": "\U0001F31F",
        ":sparkles:": "\U00002728",
        ":bulb:": "\U0001F4A1",
        ":thought_balloon:": "\U0001F4AD",
        ":rocket:": "\U0001F680",
        ":fire:": "\U0001F525",
        ":zap:": "\U000026A1",
        ":boom:": "\U0001F4A5",
        ":thumbsup:": "\U0001F44D",
        ":thumbsdown:": "\U0001F44E",
        ":clap:": "\U0001F44F",
        ":wave:": "\U0001F44B",
        ":point_right:": "\U0001F449",
        ":point_left:": "\U0001F448",
        ":point_up:": "\U0001F446",
        ":point_down:": "\U0001F447",
        ":raised_hands:": "\U0001F64C",
        ":pray:": "\U0001F64F",
        ":muscle:": "\U0001F4AA",
        ":eyes:": "\U0001F440",
        ":brain:": "\U0001F9E0",
        ":heart:": "\U00002764",
        ":white_check_mark:": "\U00002705",
        ":x:": "\U0000274C",
        ":warning:": "\U000026A0",
        ":question:": "\U00002753",
        ":exclamation:": "\U00002757",
        ":calendar:": "\U0001F4C5",
        ":clock1:": "\U0001F550",
        ":clock2:": "\U0001F551",
        ":clock3:": "\U0001F552",
        ":clock4:": "\U0001F553",
        ":hourglass:": "\U0000231B",
        ":stopwatch:": "\U000023F1",
        ":timer_clock:": "\U000023F2",
        ":check:": "\U00002714",
        ":heavy_check_mark:": "\U00002714",
        ":ballot_box_with_check:": "\U00002611",
        ":link:": "\U0001F517",
        ":paperclip:": "\U0001F4CE",
        ":file_folder:": "\U0001F4C1",
        ":open_file_folder:": "\U0001F4C2",
        ":page_facing_up:": "\U0001F4C4",
        ":book:": "\U0001F4D6",
        ":books:": "\U0001F4DA",
        ":pencil:": "\U0000270F",
        ":pencil2:": "\U0000270F",
        ":pen:": "\U0001F58A",
        ":computer:": "\U0001F4BB",
        ":desktop_computer:": "\U0001F5A5",
        ":keyboard:": "\U00002328",
        ":email:": "\U0001F4E7",
        ":envelope:": "\U00002709",
        ":telephone:": "\U0000260E",
        ":iphone:": "\U0001F4F1",
        ":house:": "\U0001F3E0",
        ":office:": "\U0001F3E2",
        ":gear:": "\U00002699",
        ":wrench:": "\U0001F527",
        ":hammer:": "\U0001F528",
        ":hammer_and_wrench:": "\U0001F6E0",
        ":mag:": "\U0001F50D",
        ":mag_right:": "\U0001F50E",
        ":lock:": "\U0001F512",
        ":unlock:": "\U0001F513",
        ":key:": "\U0001F511",
        ":shield:": "\U0001F6E1",
        ":chart_with_upwards_trend:": "\U0001F4C8",
        ":chart_with_downwards_trend:": "\U0001F4C9",
        ":bar_chart:": "\U0001F4CA",
        ":moneybag:": "\U0001F4B0",
        ":dollar:": "\U0001F4B5",
        ":credit_card:": "\U0001F4B3",
        ":trophy:": "\U0001F3C6",
        ":medal:": "\U0001F3C5",
        ":crown:": "\U0001F451",
        ":gem:": "\U0001F48E",
        ":bell:": "\U0001F514",
        ":no_bell:": "\U0001F515",
        ":loud_sound:": "\U0001F50A",
        ":mute:": "\U0001F507",
        ":speaker:": "\U0001F508",
        ":mega:": "\U0001F4E3",
        ":loudspeaker:": "\U0001F4E2",
        ":one:": "\U00000031\U0000FE0F\U000020E3",
        ":two:": "\U00000032\U0000FE0F\U000020E3",
        ":three:": "\U00000033\U0000FE0F\U000020E3",
        ":four:": "\U00000034\U0000FE0F\U000020E3",
        ":five:": "\U00000035\U0000FE0F\U000020E3",
        ":arrow_right:": "\U000027A1",
        ":arrow_left:": "\U00002B05",
        ":arrow_up:": "\U00002B06",
        ":arrow_down:": "\U00002B07",
        ":arrow_forward:": "\U000025B6",
        ":arrows_counterclockwise:": "\U0001F504",
        ":repeat:": "\U0001F501",
        ":tada:": "\U0001F389",
        ":confetti_ball:": "\U0001F38A",
        ":balloon:": "\U0001F388",
        ":gift:": "\U0001F381",
        ":cake:": "\U0001F370",
        ":coffee:": "\U00002615",
        ":tea:": "\U0001F375",
        ":beers:": "\U0001F37B",
        ":pizza:": "\U0001F355",
        ":hamburger:": "\U0001F354",
        ":fries:": "\U0001F35F",
        ":smiley:": "\U0001F603",
        ":smile:": "\U0001F604",
        ":grinning:": "\U0001F600",
        ":grin:": "\U0001F601",
        ":laughing:": "\U0001F606",
        ":sweat_smile:": "\U0001F605",
        ":joy:": "\U0001F602",
        ":rofl:": "\U0001F923",
        ":wink:": "\U0001F609",
        ":blush:": "\U0001F60A",
        ":innocent:": "\U0001F607",
        ":thinking:": "\U0001F914",
        ":thinking_face:": "\U0001F914",
        ":confused:": "\U0001F615",
        ":worried:": "\U0001F61F",
        ":cry:": "\U0001F622",
        ":sob:": "\U0001F62D",
        ":angry:": "\U0001F620",
        ":rage:": "\U0001F621",
        ":sunglasses:": "\U0001F60E",
        ":nerd_face:": "\U0001F913",
        ":partying_face:": "\U0001F973",
        ":hugging_face:": "\U0001F917",
        ":shrug:": "\U0001F937",
        ":man-shrugging:": "\U0001F937\U0000200D\U00002642\U0000FE0F",
        ":woman-shrugging:": "\U0001F937\U0000200D\U00002640\U0000FE0F",
        ":100:": "\U0001F4AF",
        ":plus1:": "\U0001F44D",
        ":+1:": "\U0001F44D",
        ":-1:": "\U0001F44E",
        ":ok_hand:": "\U0001F44C",
        ":v:": "\U0000270C",
        ":crossed_fingers:": "\U0001F91E",
        ":metal:": "\U0001F918",
        ":call_me_hand:": "\U0001F919",
        ":handshake:": "\U0001F91D",
        ":writing_hand:": "\U0000270D",
        ":nail_care:": "\U0001F485",
        ":selfie:": "\U0001F933",
        ":see_no_evil:": "\U0001F648",
        ":hear_no_evil:": "\U0001F649",
        ":speak_no_evil:": "\U0001F64A",
        ":monkey:": "\U0001F412",
        ":dog:": "\U0001F436",
        ":cat:": "\U0001F431",
        ":unicorn:": "\U0001F984",
        ":rainbow:": "\U0001F308",
        ":sun_with_face:": "\U0001F31E",
        ":sunny:": "\U00002600",
        ":cloud:": "\U00002601",
        ":rain_cloud:": "\U0001F327",
        ":snowflake:": "\U00002744",
        ":snowman:": "\U00002603",
        ":earth_americas:": "\U0001F30E",
        ":earth_africa:": "\U0001F30D",
        ":earth_asia:": "\U0001F30F",
        ":globe_with_meridians:": "\U0001F310",
    }

    # Slack user ID to name mapping (will be populated dynamically)
    USER_NAME_CACHE = {}

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to Markdown, preserving structure and converting emoji codes."""
        import html as html_lib

        if not html:
            return ""

        text = html

        # Decode HTML entities first
        text = html_lib.unescape(text)

        # Convert headings
        text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n#### \1\n', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<h5[^>]*>(.*?)</h5>', r'\n##### \1\n', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<h6[^>]*>(.*?)</h6>', r'\n###### \1\n', text, flags=re.DOTALL | re.IGNORECASE)

        # Convert bold/strong
        text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)

        # Convert italic/em
        text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)

        # Convert strikethrough
        text = re.sub(r'<s[^>]*>(.*?)</s>', r'~~\1~~', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<strike[^>]*>(.*?)</strike>', r'~~\1~~', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<del[^>]*>(.*?)</del>', r'~~\1~~', text, flags=re.DOTALL | re.IGNORECASE)

        # Convert code
        text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text, flags=re.DOTALL | re.IGNORECASE)

        # Convert pre/code blocks
        text = re.sub(r'<pre[^>]*>(.*?)</pre>', r'\n```\n\1\n```\n', text, flags=re.DOTALL | re.IGNORECASE)

        # Convert links - extract href and text
        text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL | re.IGNORECASE)

        # Convert blockquotes
        def convert_blockquote(match):
            content = match.group(1).strip()
            lines = content.split('\n')
            return '\n' + '\n'.join(f'> {line}' for line in lines) + '\n'
        text = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', convert_blockquote, text, flags=re.DOTALL | re.IGNORECASE)

        # Convert unordered lists - handle list items first
        def convert_ul(match):
            content = match.group(1)
            items = re.findall(r'<li[^>]*>(.*?)</li>', content, flags=re.DOTALL | re.IGNORECASE)
            return '\n' + '\n'.join(f'- {item.strip()}' for item in items) + '\n'
        text = re.sub(r'<ul[^>]*>(.*?)</ul>', convert_ul, text, flags=re.DOTALL | re.IGNORECASE)

        # Convert ordered lists
        def convert_ol(match):
            content = match.group(1)
            items = re.findall(r'<li[^>]*>(.*?)</li>', content, flags=re.DOTALL | re.IGNORECASE)
            return '\n' + '\n'.join(f'{i+1}. {item.strip()}' for i, item in enumerate(items)) + '\n'
        text = re.sub(r'<ol[^>]*>(.*?)</ol>', convert_ol, text, flags=re.DOTALL | re.IGNORECASE)

        # Convert horizontal rules
        text = re.sub(r'<hr[^>]*/?>', r'\n---\n', text, flags=re.IGNORECASE)

        # Convert line breaks
        text = re.sub(r'<br[^>]*/?>', '\n', text, flags=re.IGNORECASE)

        # Convert paragraphs
        text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', text, flags=re.DOTALL | re.IGNORECASE)

        # Convert divs to line breaks
        text = re.sub(r'<div[^>]*>(.*?)</div>', r'\n\1\n', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Convert Slack emoji codes to actual emojis
        for code, emoji in self.EMOJI_MAP.items():
            text = text.replace(code, emoji)

        # Handle any remaining emoji codes (format: :emoji_name:) - leave as-is or try skin tones
        # For unknown emojis, just leave them as-is

        # Convert Slack user mentions (@UXXXXXXXX) to names
        def replace_user_mention(match):
            user_id = match.group(1)
            # Try to get from cache first
            if user_id in self.USER_NAME_CACHE:
                return f"@{self.USER_NAME_CACHE[user_id]}"
            # Try to fetch user info
            try:
                user_info = self.client.users_info(user=user_id)
                if user_info.get("ok"):
                    name = user_info.get("user", {}).get("real_name") or user_info.get("user", {}).get("name", user_id)
                    self.USER_NAME_CACHE[user_id] = name
                    return f"@{name}"
            except Exception:
                pass
            return f"@{user_id}"

        text = re.sub(r'@(U[A-Z0-9]{8,})', replace_user_mention, text)

        # Also handle <@UXXXXXXXX> format
        text = re.sub(r'<@(U[A-Z0-9]{8,})>', replace_user_mention, text)

        # Clean up excessive whitespace while preserving intentional formatting
        # Remove more than 3 consecutive newlines
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        # Clean up spaces around newlines
        text = re.sub(r' *\n *', '\n', text)
        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    @staticmethod
    def parse_date_to_timestamp(date_str: str) -> float:
        """Convert ISO date string to Unix timestamp."""
        if not date_str:
            return None

        # Try various formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.timestamp()
            except ValueError:
                continue

        raise ValueError(f"Could not parse date: {date_str}. Use format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")

    @staticmethod
    def format_timestamp(ts: float) -> str:
        """Convert Unix timestamp to readable format."""
        return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")


# --- CLI Interface ---

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Slack API CLI - Manage channels, messages, pins, and canvases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest="category", help="Command category")

    # === Channels ===
    channels_parser = subparsers.add_parser("channels", help="Channel operations")
    channels_sub = channels_parser.add_subparsers(dest="action")

    # channels list
    list_parser = channels_sub.add_parser("list", help="List channels")
    list_parser.add_argument("--type", choices=["public", "private", "all"], default="all",
                            help="Channel type filter")
    list_parser.add_argument("--include-archived", action="store_true", help="Include archived channels")

    # channels create
    create_parser = channels_sub.add_parser("create", help="Create a channel")
    create_parser.add_argument("name", help="Channel name")
    create_parser.add_argument("--private", action="store_true", help="Create as private channel")
    create_parser.add_argument("--description", help="Channel description/purpose")

    # channels rename
    rename_parser = channels_sub.add_parser("rename", help="Rename a channel")
    rename_parser.add_argument("channel", help="Channel ID or current name")
    rename_parser.add_argument("new_name", help="New channel name")

    # channels archive
    archive_parser = channels_sub.add_parser("archive", help="Archive a channel")
    archive_parser.add_argument("channel", help="Channel ID or name")

    # channels unarchive
    unarchive_parser = channels_sub.add_parser("unarchive", help="Unarchive a channel")
    unarchive_parser.add_argument("channel", help="Channel ID or name")

    # channels join
    join_parser = channels_sub.add_parser("join", help="Join a public channel")
    join_parser.add_argument("channel", help="Channel ID or name")

    # channels join-all
    channels_sub.add_parser("join-all", help="Join all public channels")

    # channels info
    info_parser = channels_sub.add_parser("info", help="Get channel info")
    info_parser.add_argument("channel", help="Channel ID or name")

    # channels set-topic
    topic_parser = channels_sub.add_parser("set-topic", help="Set channel topic")
    topic_parser.add_argument("channel", help="Channel ID or name")
    topic_parser.add_argument("topic", help="New topic text")

    # channels set-purpose
    purpose_parser = channels_sub.add_parser("set-purpose", help="Set channel purpose")
    purpose_parser.add_argument("channel", help="Channel ID or name")
    purpose_parser.add_argument("purpose", help="New purpose text")

    # === Messages ===
    messages_parser = subparsers.add_parser("messages", help="Message operations")
    messages_sub = messages_parser.add_subparsers(dest="action")

    # messages get
    get_parser = messages_sub.add_parser("get", help="Get messages from a channel")
    get_parser.add_argument("channel", help="Channel ID or name")
    get_parser.add_argument("--days", type=int, help="Get messages from last N days")
    get_parser.add_argument("--hours", type=int, help="Get messages from last N hours")
    get_parser.add_argument("--since", help="Start date (ISO format: YYYY-MM-DD)")
    get_parser.add_argument("--until", help="End date (ISO format: YYYY-MM-DD)")
    get_parser.add_argument("--limit", type=int, default=100, help="Max messages to retrieve")
    get_parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format")
    get_parser.add_argument("--output", help="Write output to file")

    # messages get-multi
    getmulti_parser = messages_sub.add_parser("get-multi", help="Get messages from multiple channels")
    getmulti_parser.add_argument("channels", nargs="+", help="Channel IDs or names")
    getmulti_parser.add_argument("--days", type=int, help="Get messages from last N days")
    getmulti_parser.add_argument("--hours", type=int, help="Get messages from last N hours")
    getmulti_parser.add_argument("--since", help="Start date (ISO format)")
    getmulti_parser.add_argument("--until", help="End date (ISO format)")
    getmulti_parser.add_argument("--limit", type=int, default=100, help="Max messages per channel")

    # messages clear
    clear_parser = messages_sub.add_parser("clear", help="Delete all messages from channel(s)")
    clear_parser.add_argument("channels", nargs="+", help="Channel IDs or names")
    clear_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")

    # === Pins ===
    pins_parser = subparsers.add_parser("pins", help="Pin operations")
    pins_sub = pins_parser.add_subparsers(dest="action")

    # pins list
    pins_list = pins_sub.add_parser("list", help="List pinned items")
    pins_list.add_argument("channel", help="Channel ID or name")

    # pins add
    pins_add = pins_sub.add_parser("add", help="Pin a message")
    pins_add.add_argument("channel", help="Channel ID or name")
    pins_add.add_argument("message_ts", help="Message timestamp to pin")

    # pins remove
    pins_remove = pins_sub.add_parser("remove", help="Remove a pin")
    pins_remove.add_argument("channel", help="Channel ID or name")
    pins_remove.add_argument("message_ts", help="Message timestamp to unpin")

    # === Groups (User Groups) ===
    groups_parser = subparsers.add_parser("groups", help="User group operations (for sidebar sections)")
    groups_sub = groups_parser.add_subparsers(dest="action")

    # groups list
    groups_list = groups_sub.add_parser("list", help="List user groups")
    groups_list.add_argument("--include-disabled", action="store_true", help="Include disabled groups")

    # groups create
    groups_create = groups_sub.add_parser("create", help="Create a user group with sidebar section")
    groups_create.add_argument("name", help="Group display name (e.g., 'Client - Acme')")
    groups_create.add_argument("--handle", help="Mention handle without @ (defaults to slugified name)")
    groups_create.add_argument("--description", help="Group description")
    groups_create.add_argument("--channels", nargs="+", help="Default channels for group members")
    groups_create.add_argument("--users", nargs="+", help="User IDs to add to the group")

    # groups update
    groups_update = groups_sub.add_parser("update", help="Update a user group")
    groups_update.add_argument("group_id", help="User group ID")
    groups_update.add_argument("--name", help="New display name")
    groups_update.add_argument("--handle", help="New mention handle")
    groups_update.add_argument("--description", help="New description")
    groups_update.add_argument("--channels", nargs="+", help="New default channels")

    # groups members
    groups_members = groups_sub.add_parser("members", help="Get or set group members")
    groups_members.add_argument("group_id", help="User group ID")
    groups_members.add_argument("--set", nargs="+", dest="set_users", help="Set members (replaces existing)")

    # groups disable
    groups_disable = groups_sub.add_parser("disable", help="Disable (archive) a user group")
    groups_disable.add_argument("group_id", help="User group ID")

    # groups enable
    groups_enable = groups_sub.add_parser("enable", help="Re-enable a disabled user group")
    groups_enable.add_argument("group_id", help="User group ID")

    # === Users ===
    users_parser = subparsers.add_parser("users", help="User operations")
    users_sub = users_parser.add_subparsers(dest="action")

    # users list
    users_list = users_sub.add_parser("list", help="List workspace users")

    # users invite
    users_invite = users_sub.add_parser("invite", help="Invite users to a channel")
    users_invite.add_argument("channel", help="Channel ID or name")
    users_invite.add_argument("users", nargs="+", help="User IDs to invite")

    # users invite-all
    users_invite_all = users_sub.add_parser("invite-all", help="Invite all workspace users to channels")
    users_invite_all.add_argument("channels", nargs="+", help="Channel IDs or names")

    # === Canvas ===
    canvas_parser = subparsers.add_parser("canvas", help="Canvas operations")
    canvas_sub = canvas_parser.add_subparsers(dest="action")

    # canvas create
    canvas_create = canvas_sub.add_parser("create", help="Create channel canvas")
    canvas_create.add_argument("channel", help="Channel ID or name")
    canvas_create.add_argument("--markdown", help="Initial markdown content")
    canvas_create.add_argument("--markdown-file", help="File containing markdown content")

    # canvas update
    canvas_update = canvas_sub.add_parser("update", help="Update channel canvas")
    canvas_update.add_argument("channel", help="Channel ID or name")
    canvas_update.add_argument("--markdown", help="New markdown content")
    canvas_update.add_argument("--markdown-file", help="File containing markdown content")

    # canvas get
    canvas_get = canvas_sub.add_parser("get", help="Get channel canvas")
    canvas_get.add_argument("channel", help="Channel ID or name")

    # === Client ===
    client_parser = subparsers.add_parser("client", help="Client onboarding operations")
    client_sub = client_parser.add_subparsers(dest="action")

    # client setup
    client_setup = client_sub.add_parser("setup", help="Set up channels for a new client")
    client_setup.add_argument("slug", help="Client slug for channel names (e.g., 'acme' -> #acme, #acme-internal)")
    client_setup.add_argument("--display-name", help="Human-readable client name (defaults to titleized slug)")
    client_setup.add_argument("--canvas-template", default="templates/client_canvas.md",
                              help="Path to canvas markdown template")
    client_setup.add_argument("--welcome-template", default="templates/client_welcome.md",
                              help="Path to welcome message markdown template")
    client_setup.add_argument("--notify-channel", default="#new-clients",
                              help="Channel to post notification about new client (default: #new-clients)")
    client_setup.add_argument("--no-notify", action="store_true",
                              help="Skip posting notification to team channel")

    # === Huddles ===
    huddles_parser = subparsers.add_parser("huddles", help="Huddle operations (meetings with notes)")
    huddles_sub = huddles_parser.add_subparsers(dest="action")

    # huddles find
    huddles_find = huddles_sub.add_parser("find", help="Find huddles in a channel")
    huddles_find.add_argument("channel", help="Channel ID or name")
    huddles_find.add_argument("--days", type=int, help="Get huddles from last N days")
    huddles_find.add_argument("--hours", type=int, help="Get huddles from last N hours")
    huddles_find.add_argument("--since", help="Start date (ISO format: YYYY-MM-DD)")
    huddles_find.add_argument("--until", help="End date (ISO format: YYYY-MM-DD)")
    huddles_find.add_argument("--limit", type=int, default=500, help="Max messages to scan")
    huddles_find.add_argument("--output", help="Write output to file")

    # huddles find-all
    huddles_find_all = huddles_sub.add_parser("find-all", help="Find huddles across all channels")
    huddles_find_all.add_argument("--channels", nargs="+", help="Specific channels to search (default: all)")
    huddles_find_all.add_argument("--days", type=int, help="Get huddles from last N days")
    huddles_find_all.add_argument("--hours", type=int, help="Get huddles from last N hours")
    huddles_find_all.add_argument("--since", help="Start date (ISO format)")
    huddles_find_all.add_argument("--until", help="End date (ISO format)")
    huddles_find_all.add_argument("--limit", type=int, default=500, help="Max messages per channel")
    huddles_find_all.add_argument("--output", help="Write output to file")

    # huddles notes
    huddles_notes = huddles_sub.add_parser("notes", help="Get huddle notes canvas content")
    huddles_notes.add_argument("file_id", help="Huddle notes canvas file ID")

    # huddles transcript
    huddles_transcript = huddles_sub.add_parser("transcript", help="Get raw huddle transcript content")
    huddles_transcript.add_argument("file_id", help="Huddle transcript file ID (from notes.huddle_transcript_file_id)")

    return parser


def format_messages_as_text(messages: List[Dict], client: SlackClient) -> str:
    """Format messages as human-readable text."""
    lines = []
    for msg in messages:
        ts = SlackClient.format_timestamp(msg.get("ts", 0))
        user = msg.get("user", "unknown")
        # Try to get username (expensive, so cache would help in production)
        text = msg.get("text", "")
        lines.append(f"[{ts}] <{user}> {text}")
    return "\n".join(lines)


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.category:
        parser.print_help()
        sys.exit(1)

    try:
        client = SlackClient()
    except (ValueError, ImportError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # === Channels ===
        if args.category == "channels":
            if args.action == "list":
                types_map = {
                    "public": "public_channel",
                    "private": "private_channel",
                    "all": "public_channel,private_channel"
                }
                channels = client.list_channels(
                    types=types_map[args.type],
                    exclude_archived=not args.include_archived
                )
                print(f"Found {len(channels)} channel(s):", file=sys.stderr)
                print(json.dumps(channels, indent=2))

            elif args.action == "create":
                channel = client.create_channel(
                    args.name,
                    is_private=args.private,
                    description=args.description
                )
                print(f"Created channel: {channel.get('id')} - #{channel.get('name')}", file=sys.stderr)
                print(json.dumps(channel, indent=2))

            elif args.action == "rename":
                channel = client.rename_channel(args.channel, args.new_name)
                print(f"Renamed to: #{channel.get('name')}")

            elif args.action == "archive":
                client.archive_channel(args.channel)
                print(f"Archived channel: {args.channel}")

            elif args.action == "unarchive":
                client.unarchive_channel(args.channel)
                print(f"Unarchived channel: {args.channel}")

            elif args.action == "info":
                info = client.get_channel_info(args.channel)
                print(json.dumps(info, indent=2))

            elif args.action == "set-topic":
                result = client.set_channel_topic(args.channel, args.topic)
                print(f"Set topic: {result}")

            elif args.action == "set-purpose":
                result = client.set_channel_purpose(args.channel, args.purpose)
                print(f"Set purpose: {result}")

            elif args.action == "join":
                channel = client.join_channel(args.channel)
                print(f"Joined channel: #{channel.get('name')}")

            elif args.action == "join-all":
                results = client.join_all_channels()
                joined = [k for k, v in results.items() if v]
                failed = [k for k, v in results.items() if not v]
                print(f"Joined {len(joined)} channels:")
                for ch in joined:
                    print(f"  ✓ #{ch}")
                if failed:
                    print(f"\nFailed to join {len(failed)} channels:")
                    for ch in failed:
                        print(f"  ✗ #{ch}")
            else:
                parser.parse_args(["channels", "--help"])

        # === Messages ===
        elif args.category == "messages":
            if args.action == "get":
                oldest = None
                latest = None

                if args.days:
                    oldest = (datetime.now() - timedelta(days=args.days)).timestamp()
                elif args.hours:
                    oldest = (datetime.now() - timedelta(hours=args.hours)).timestamp()
                elif args.since:
                    oldest = SlackClient.parse_date_to_timestamp(args.since)

                if args.until:
                    latest = SlackClient.parse_date_to_timestamp(args.until)

                messages = client.get_messages(
                    args.channel,
                    oldest=oldest,
                    latest=latest,
                    limit=args.limit
                )

                print(f"Retrieved {len(messages)} message(s)", file=sys.stderr)

                if args.format == "text":
                    output = format_messages_as_text(messages, client)
                else:
                    output = json.dumps(messages, indent=2)

                if args.output:
                    with open(args.output, 'w') as f:
                        f.write(output)
                    print(f"Written to {args.output}", file=sys.stderr)
                else:
                    print(output)

            elif args.action == "get-multi":
                oldest = None
                latest = None

                if args.days:
                    oldest = (datetime.now() - timedelta(days=args.days)).timestamp()
                elif args.hours:
                    oldest = (datetime.now() - timedelta(hours=args.hours)).timestamp()
                elif args.since:
                    oldest = SlackClient.parse_date_to_timestamp(args.since)

                if args.until:
                    latest = SlackClient.parse_date_to_timestamp(args.until)

                result = client.get_messages_multi(
                    args.channels,
                    oldest=oldest,
                    latest=latest,
                    limit_per_channel=args.limit
                )

                total = sum(len(msgs) for msgs in result.values())
                print(f"Retrieved {total} message(s) from {len(args.channels)} channel(s)", file=sys.stderr)
                print(json.dumps(result, indent=2))

            elif args.action == "clear":
                if not client.user_client:
                    print("Error: SLACK_USER_TOKEN required to delete messages. Set it in .env", file=sys.stderr)
                    sys.exit(1)

                total_deleted = 0
                for channel in args.channels:
                    try:
                        channel_id = client.resolve_channel(channel)
                        messages = client.get_messages(channel_id, limit=1000)

                        if args.dry_run:
                            print(f"#{channel}: Would delete {len(messages)} message(s)", file=sys.stderr)
                            total_deleted += len(messages)
                            continue

                        deleted = 0
                        for msg in messages:
                            try:
                                client.delete_message(channel_id, msg["ts"], use_user_token=True)
                                deleted += 1
                            except SlackError as e:
                                # Some system messages can't be deleted
                                print(f"  Could not delete message: {e}", file=sys.stderr)

                        print(f"#{channel}: Deleted {deleted}/{len(messages)} message(s)", file=sys.stderr)
                        total_deleted += deleted
                    except SlackError as e:
                        print(f"#{channel}: Error - {e}", file=sys.stderr)

                action = "Would delete" if args.dry_run else "Deleted"
                print(f"\n{action} {total_deleted} total message(s) from {len(args.channels)} channel(s)")
            else:
                parser.parse_args(["messages", "--help"])

        # === Pins ===
        elif args.category == "pins":
            if args.action == "list":
                pins = client.list_pins(args.channel)
                print(f"Found {len(pins)} pinned item(s)", file=sys.stderr)
                print(json.dumps(pins, indent=2))

            elif args.action == "add":
                client.add_pin(args.channel, args.message_ts)
                print(f"Pinned message {args.message_ts} in {args.channel}")

            elif args.action == "remove":
                client.remove_pin(args.channel, args.message_ts)
                print(f"Unpinned message {args.message_ts} in {args.channel}")
            else:
                parser.parse_args(["pins", "--help"])

        # === Groups (User Groups) ===
        elif args.category == "groups":
            if args.action == "list":
                groups = client.list_usergroups(include_disabled=args.include_disabled)
                print(f"Found {len(groups)} user group(s):", file=sys.stderr)
                for g in groups:
                    status = " (disabled)" if g.get("date_delete", 0) > 0 else ""
                    print(f"  {g.get('id')} - @{g.get('handle')} - {g.get('name')}{status}", file=sys.stderr)
                print(json.dumps(groups, indent=2))

            elif args.action == "create":
                group = client.create_usergroup(
                    name=args.name,
                    handle=args.handle,
                    description=args.description,
                    channels=args.channels,
                    users=args.users
                )
                print(f"Created user group: {group.get('id')} - @{group.get('handle')}", file=sys.stderr)
                print(json.dumps(group, indent=2))

            elif args.action == "update":
                group = client.update_usergroup(
                    usergroup_id=args.group_id,
                    name=args.name,
                    handle=args.handle,
                    description=args.description,
                    channels=args.channels
                )
                print(f"Updated user group: {group.get('id')}", file=sys.stderr)
                print(json.dumps(group, indent=2))

            elif args.action == "members":
                if args.set_users:
                    group = client.update_usergroup_members(args.group_id, args.set_users)
                    print(f"Updated members for {args.group_id}", file=sys.stderr)
                    print(json.dumps(group, indent=2))
                else:
                    members = client.get_usergroup_members(args.group_id)
                    print(f"Found {len(members)} member(s):", file=sys.stderr)
                    for uid in members:
                        name = client.get_user_name(uid)
                        print(f"  {uid} - {name}", file=sys.stderr)
                    print(json.dumps(members, indent=2))

            elif args.action == "disable":
                group = client.disable_usergroup(args.group_id)
                print(f"Disabled user group: {args.group_id}")

            elif args.action == "enable":
                group = client.enable_usergroup(args.group_id)
                print(f"Enabled user group: {args.group_id}")

            else:
                parser.parse_args(["groups", "--help"])

        # === Users ===
        elif args.category == "users":
            if args.action == "list":
                users = client.list_users()
                print(f"Found {len(users)} user(s):", file=sys.stderr)
                for user in users:
                    print(f"  {user.get('id')} - {user.get('real_name', user.get('name'))}", file=sys.stderr)
                print(json.dumps(users, indent=2))

            elif args.action == "invite":
                result = client.invite_users(args.channel, args.users)
                print(f"Invited {len(args.users)} user(s) to {args.channel}")

            elif args.action == "invite-all":
                users = client.list_users()
                user_ids = [u["id"] for u in users]
                print(f"Inviting {len(user_ids)} user(s) to {len(args.channels)} channel(s)...", file=sys.stderr)

                for channel in args.channels:
                    try:
                        client.invite_users(channel, user_ids)
                        print(f"  ✓ Invited all users to {channel}", file=sys.stderr)
                    except SlackError as e:
                        # already_in_channel is common, don't fail
                        if "already_in_channel" in str(e):
                            print(f"  ✓ Users already in {channel}", file=sys.stderr)
                        else:
                            print(f"  ✗ Failed to invite to {channel}: {e}", file=sys.stderr)

                print("Done!")
            else:
                parser.parse_args(["users", "--help"])

        # === Canvas ===
        elif args.category == "canvas":
            if args.action == "create":
                content = args.markdown
                if args.markdown_file:
                    with open(args.markdown_file, 'r') as f:
                        content = f.read()

                result = client.create_channel_canvas(args.channel, content)
                print(f"Created canvas for {args.channel}", file=sys.stderr)
                print(json.dumps(result, indent=2))

            elif args.action == "update":
                content = args.markdown
                if args.markdown_file:
                    with open(args.markdown_file, 'r') as f:
                        content = f.read()

                if not content:
                    print("Error: --markdown or --markdown-file required", file=sys.stderr)
                    sys.exit(1)

                client.update_channel_canvas(args.channel, content)
                print(f"Updated canvas for {args.channel}")

            elif args.action == "get":
                result = client.get_channel_canvas(args.channel)
                print(json.dumps(result, indent=2))
            else:
                parser.parse_args(["canvas", "--help"])

        # === Client ===
        elif args.category == "client":
            if args.action == "setup":
                result = client.setup_client(
                    client_slug=args.slug,
                    display_name=args.display_name,
                    canvas_template_path=args.canvas_template,
                    welcome_template_path=args.welcome_template,
                    notification_channel=None if args.no_notify else args.notify_channel
                )
                print(json.dumps(result, indent=2))
            else:
                parser.parse_args(["client", "--help"])

        # === Huddles ===
        elif args.category == "huddles":
            if args.action == "find":
                huddles = client.find_huddles(
                    channel=args.channel,
                    days=args.days,
                    hours=args.hours,
                    since=args.since,
                    until=args.until,
                    limit=args.limit
                )

                print(f"Found {len(huddles)} huddle(s)", file=sys.stderr)
                for h in huddles:
                    notes_info = f" - Notes: {h['notes']['title']}" if h.get('notes') else " - No notes"
                    print(f"  {h['date_start_formatted']} ({h['duration_seconds']}s, {h['participant_count']} participants){notes_info}", file=sys.stderr)

                output = json.dumps(huddles, indent=2)
                if args.output:
                    with open(args.output, 'w') as f:
                        f.write(output)
                    print(f"Written to {args.output}", file=sys.stderr)
                else:
                    print(output)

            elif args.action == "find-all":
                result = client.find_huddles_multi(
                    channels=args.channels,
                    days=args.days,
                    hours=args.hours,
                    since=args.since,
                    until=args.until,
                    limit_per_channel=args.limit
                )

                total_huddles = sum(len(h) for h in result.values())
                print(f"Found {total_huddles} huddle(s) across {len(result)} channel(s)", file=sys.stderr)
                for channel_id, huddles in result.items():
                    print(f"  #{channel_id}: {len(huddles)} huddle(s)", file=sys.stderr)

                output = json.dumps(result, indent=2)
                if args.output:
                    with open(args.output, 'w') as f:
                        f.write(output)
                    print(f"Written to {args.output}", file=sys.stderr)
                else:
                    print(output)

            elif args.action == "notes":
                result = client.get_huddle_notes_content(args.file_id)
                print(json.dumps(result, indent=2))

            elif args.action == "transcript":
                result = client.get_transcript_content(args.file_id)
                if result.get("error"):
                    print(f"Error: {result['error']}", file=sys.stderr)
                    sys.exit(1)
                print(f"Retrieved transcript: {result.get('name')} ({result.get('filetype')}, {result.get('size')} bytes)", file=sys.stderr)
                print(json.dumps(result, indent=2))

            else:
                parser.parse_args(["huddles", "--help"])

        else:
            parser.print_help()
            sys.exit(1)

    except SlackError as e:
        print(f"Slack API error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

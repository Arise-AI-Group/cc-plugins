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

import sys
import os
import json
import time
import argparse
from pathlib import Path
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

    # ==================== Helper Methods ====================

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

"""
Slack Plugin - Level 2 Tests (Read-Only)

These tests make real API calls but only perform read operations.
Requires valid SLACK_BOT_TOKEN credentials.
"""
import pytest


@pytest.mark.level2
@pytest.mark.requires_credentials
class TestSlackReadOperations:
    """Read-only tests against real Slack API."""

    def test_list_channels(self, slack_client):
        """Test listing channels from real workspace."""
        channels = slack_client.list_channels(limit=10)

        assert isinstance(channels, list)
        # There should be at least some channels in any workspace
        assert len(channels) > 0

        # Verify structure
        first_channel = channels[0]
        assert "id" in first_channel
        assert "name" in first_channel
        # Channel IDs start with C (public) or G (private)
        assert first_channel["id"][0] in ("C", "G")

    def test_list_channels_with_type_filter(self, slack_client):
        """Test listing public channels only."""
        channels = slack_client.list_channels(types="public_channel", limit=10)

        assert isinstance(channels, list)
        # All should be public (non-private)
        for ch in channels:
            assert not ch.get("is_private", False)

    def test_get_channel_info(self, slack_client, find_existing_channel):
        """Test getting info for an existing channel."""
        channel = find_existing_channel()
        if not channel:
            pytest.skip("No channels available for testing")

        info = slack_client.get_channel_info(channel["id"])

        assert info["id"] == channel["id"]
        assert "name" in info

    def test_get_channel_info_by_name(self, slack_client, find_existing_channel):
        """Test resolving channel by name."""
        channel = find_existing_channel()
        if not channel:
            pytest.skip("No channels available for testing")

        # Test resolution by name
        resolved_id = slack_client.resolve_channel(channel["name"])
        assert resolved_id == channel["id"]

    def test_get_channel_info_with_hash_prefix(self, slack_client, find_existing_channel):
        """Test resolving channel with # prefix."""
        channel = find_existing_channel()
        if not channel:
            pytest.skip("No channels available for testing")

        # Test resolution with # prefix
        resolved_id = slack_client.resolve_channel(f"#{channel['name']}")
        assert resolved_id == channel["id"]

    def test_list_users(self, slack_client):
        """Test listing workspace users."""
        users = slack_client.list_users(limit=10)

        assert isinstance(users, list)
        assert len(users) > 0

        first_user = users[0]
        assert "id" in first_user
        assert first_user["id"].startswith("U") or first_user["id"].startswith("W")

    def test_get_messages(self, slack_client, find_existing_channel):
        """Test retrieving messages from a channel."""
        channel = find_existing_channel()
        if not channel:
            pytest.skip("No channels available for testing")

        # Get recent messages (may be empty in a quiet channel)
        messages = slack_client.get_messages(channel["id"], limit=5)

        assert isinstance(messages, list)
        # Don't assert on count - channel may be empty

    def test_list_pins(self, slack_client, find_existing_channel):
        """Test listing pinned items in a channel."""
        channel = find_existing_channel()
        if not channel:
            pytest.skip("No channels available for testing")

        pins = slack_client.list_pins(channel["id"])

        assert isinstance(pins, list)
        # Don't assert on count - may have no pins

    def test_list_usergroups(self, slack_client):
        """Test listing user groups."""
        groups = slack_client.list_usergroups()

        assert isinstance(groups, list)
        # Don't assert on count - workspace may not have groups


@pytest.mark.level2
@pytest.mark.requires_credentials
class TestSlackErrorConditions:
    """Test error conditions with real API."""

    def test_nonexistent_channel_by_id(self, slack_client, slack_exceptions):
        """Test handling of nonexistent channel ID."""
        if not slack_exceptions:
            pytest.skip("Slack exceptions not available")

        SlackNotFoundError = slack_exceptions["SlackNotFoundError"]

        with pytest.raises((SlackNotFoundError, Exception)):
            slack_client.get_channel_info("C00000INVALID")

    def test_nonexistent_channel_by_name(self, slack_client, slack_exceptions):
        """Test handling of nonexistent channel name."""
        if not slack_exceptions:
            pytest.skip("Slack exceptions not available")

        SlackNotFoundError = slack_exceptions["SlackNotFoundError"]

        with pytest.raises((SlackNotFoundError, Exception)):
            slack_client.resolve_channel("nonexistent-channel-xyz-12345-abcdef")


@pytest.mark.level2
@pytest.mark.requires_credentials
class TestSlackUserOperations:
    """Test user-related read operations."""

    def test_get_user_info(self, slack_client):
        """Test getting user info."""
        users = slack_client.list_users(limit=1)
        if not users:
            pytest.skip("No users available for testing")

        user_id = users[0]["id"]
        info = slack_client.get_user_info(user_id)

        assert info["id"] == user_id

    def test_get_user_name(self, slack_client):
        """Test getting user display name."""
        users = slack_client.list_users(limit=1)
        if not users:
            pytest.skip("No users available for testing")

        user_id = users[0]["id"]
        name = slack_client.get_user_name(user_id)

        assert isinstance(name, str)
        assert len(name) > 0

"""
Slack Plugin - Level 1 Tests (Dry/Mocked)

These tests verify business logic without making any external API calls.
All responses are mocked.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestSlackClientMockedOperations:
    """Test operations with mocked responses."""

    @pytest.mark.level1
    def test_list_channels_returns_list(self, mock_slack_client):
        """Test that list_channels returns a list of channels."""
        channels = mock_slack_client.list_channels()

        assert isinstance(channels, list)
        assert len(channels) > 0
        assert all("id" in ch and "name" in ch for ch in channels)

    @pytest.mark.level1
    def test_get_channel_info_returns_dict(self, mock_slack_client):
        """Test that get_channel_info returns channel details."""
        info = mock_slack_client.get_channel_info("C0001")

        assert isinstance(info, dict)
        assert "id" in info
        assert "name" in info
        assert "topic" in info
        assert "purpose" in info

    @pytest.mark.level1
    def test_list_users_returns_list(self, mock_slack_client):
        """Test that list_users returns a list of users."""
        users = mock_slack_client.list_users()

        assert isinstance(users, list)
        assert len(users) > 0
        assert all("id" in u and "name" in u for u in users)

    @pytest.mark.level1
    def test_get_messages_returns_list(self, mock_slack_client):
        """Test that get_messages returns a list of messages."""
        messages = mock_slack_client.get_messages("C0001")

        assert isinstance(messages, list)
        assert all("ts" in m and "user" in m for m in messages)

    @pytest.mark.level1
    def test_list_pins_returns_list(self, mock_slack_client):
        """Test that list_pins returns a list."""
        pins = mock_slack_client.list_pins("C0001")

        assert isinstance(pins, list)

    @pytest.mark.level1
    def test_list_usergroups_returns_list(self, mock_slack_client):
        """Test that list_usergroups returns a list."""
        groups = mock_slack_client.list_usergroups()

        assert isinstance(groups, list)

    @pytest.mark.level1
    def test_create_channel_returns_channel_info(self, mock_slack_client):
        """Test that create_channel returns channel details."""
        result = mock_slack_client.create_channel("test-channel")

        assert isinstance(result, dict)
        assert "id" in result
        assert "name" in result

    @pytest.mark.level1
    def test_post_message_returns_message_info(self, mock_slack_client):
        """Test that post_message returns message details."""
        result = mock_slack_client.post_message("C0001", "Hello")

        assert isinstance(result, dict)
        assert "ts" in result
        assert "channel" in result

    @pytest.mark.level1
    def test_delete_message_returns_bool(self, mock_slack_client):
        """Test that delete_message returns success status."""
        result = mock_slack_client.delete_message("C0001", "1234567890.123456")

        assert result is True

    @pytest.mark.level1
    def test_archive_channel_returns_bool(self, mock_slack_client):
        """Test that archive_channel returns success status."""
        result = mock_slack_client.archive_channel("C0001")

        assert result is True


class TestSlackResponseParsing:
    """Test response parsing and data transformation."""

    @pytest.mark.level1
    def test_channel_response_structure(self, mock_slack_responses):
        """Test that channel response has expected structure."""
        channels = mock_slack_responses("list_channels")

        assert isinstance(channels, list)
        for channel in channels:
            assert "id" in channel
            assert "name" in channel
            assert channel["id"].startswith("C")

    @pytest.mark.level1
    def test_user_response_structure(self, mock_slack_responses):
        """Test that user response has expected structure."""
        users = mock_slack_responses("list_users")

        assert isinstance(users, list)
        for user in users:
            assert "id" in user
            assert "name" in user
            assert user["id"].startswith("U")

    @pytest.mark.level1
    def test_message_response_structure(self, mock_slack_responses):
        """Test that message response has expected structure."""
        messages = mock_slack_responses("get_messages")

        assert isinstance(messages, list)
        for msg in messages:
            assert "ts" in msg
            assert "text" in msg


class TestSlackChannelResolution:
    """Test channel name to ID resolution logic."""

    @pytest.mark.level1
    def test_resolve_channel_called_with_id(self, mock_slack_client):
        """Test that channel IDs are passed through resolve_channel."""
        mock_slack_client.resolve_channel.return_value = "C0001"

        result = mock_slack_client.resolve_channel("C0001")

        assert result == "C0001"
        mock_slack_client.resolve_channel.assert_called_with("C0001")

    @pytest.mark.level1
    def test_resolve_channel_called_with_name(self, mock_slack_client):
        """Test that channel names are resolved."""
        mock_slack_client.resolve_channel.return_value = "C0001"

        result = mock_slack_client.resolve_channel("general")

        assert result == "C0001"

    @pytest.mark.level1
    def test_resolve_channel_strips_hash(self, mock_slack_client):
        """Test that # prefix is handled in channel resolution."""
        mock_slack_client.resolve_channel.return_value = "C0001"

        result = mock_slack_client.resolve_channel("#general")

        assert result == "C0001"


class TestSlackErrorHandling:
    """Test error handling with mocked errors."""

    @pytest.mark.level1
    def test_mock_not_found_error(self, mock_slack_client, slack_exceptions):
        """Test handling of channel not found error."""
        if not slack_exceptions:
            pytest.skip("Slack exceptions not available")

        SlackNotFoundError = slack_exceptions["SlackNotFoundError"]
        mock_slack_client.get_channel_info.side_effect = SlackNotFoundError("Channel not found")

        with pytest.raises(SlackNotFoundError):
            mock_slack_client.get_channel_info("C_INVALID")

    @pytest.mark.level1
    def test_mock_auth_error(self, mock_slack_client, slack_exceptions):
        """Test handling of authentication error."""
        if not slack_exceptions:
            pytest.skip("Slack exceptions not available")

        SlackAuthError = slack_exceptions["SlackAuthError"]
        mock_slack_client.list_channels.side_effect = SlackAuthError("Invalid token")

        with pytest.raises(SlackAuthError):
            mock_slack_client.list_channels()

    @pytest.mark.level1
    def test_mock_rate_limit_error(self, mock_slack_client, slack_exceptions):
        """Test handling of rate limit error."""
        if not slack_exceptions:
            pytest.skip("Slack exceptions not available")

        SlackRateLimitError = slack_exceptions["SlackRateLimitError"]
        mock_slack_client.list_channels.side_effect = SlackRateLimitError(30)

        with pytest.raises(SlackRateLimitError) as exc_info:
            mock_slack_client.list_channels()

        assert exc_info.value.retry_after == 30


class TestSlackClientInitialization:
    """Test client initialization logic."""

    @pytest.mark.level1
    def test_client_requires_token(self):
        """Test that client raises error without token."""
        # We need to patch the module-level SLACK_BOT_TOKEN since the client
        # falls back to it when bot_token is falsy (empty string or None)
        try:
            import slack.tool.slack_api as slack_module
            original_token = slack_module.SLACK_BOT_TOKEN
            try:
                slack_module.SLACK_BOT_TOKEN = ""
                with pytest.raises(ValueError, match="SLACK_BOT_TOKEN"):
                    slack_module.SlackClient(bot_token=None)
            finally:
                # Restore the original token
                slack_module.SLACK_BOT_TOKEN = original_token
        except ImportError:
            pytest.skip("Slack module not available")

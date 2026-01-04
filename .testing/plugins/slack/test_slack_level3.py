"""
Slack Plugin - Level 3 Tests (Write Operations)

These tests create real resources with test-ccplugins-* prefix and clean them up.
Requires valid SLACK_BOT_TOKEN and optionally SLACK_USER_TOKEN credentials.
"""
import pytest
import time


@pytest.mark.level3
@pytest.mark.requires_credentials
class TestSlackChannelOperations:
    """Test channel creation and management."""

    def test_create_and_archive_channel(
        self,
        slack_client,
        slack_test_channel_name,
        slack_cleanup
    ):
        """Test creating and archiving a channel."""
        channel_name = slack_test_channel_name

        # Create channel
        channel = slack_client.create_channel(
            name=channel_name,
            is_private=False,
            description="Test channel created by cc-plugins test suite"
        )

        # Register for cleanup
        slack_cleanup.register("slack_channels", {"id": channel["id"]})

        # Verify creation
        assert channel["id"].startswith("C")
        assert channel["name"] == channel_name

        # Verify we can get info
        info = slack_client.get_channel_info(channel["id"])
        assert info["id"] == channel["id"]

        # Archive (cleanup will also try, but test the method)
        result = slack_client.archive_channel(channel["id"])
        assert result is True

    def test_set_channel_topic(
        self,
        slack_client,
        slack_test_channel_name,
        slack_cleanup
    ):
        """Test setting channel topic."""
        channel_name = slack_test_channel_name

        # Create channel
        channel = slack_client.create_channel(name=channel_name)
        slack_cleanup.register("slack_channels", {"id": channel["id"]})

        # Set topic
        topic = "Test topic from cc-plugins test suite"
        result = slack_client.set_channel_topic(channel["id"], topic)

        # Verify topic was set
        assert topic in result or result == topic

        # Verify via get_channel_info
        info = slack_client.get_channel_info(channel["id"])
        assert topic in info.get("topic", {}).get("value", "")

    def test_set_channel_purpose(
        self,
        slack_client,
        slack_test_channel_name,
        slack_cleanup
    ):
        """Test setting channel purpose."""
        channel_name = slack_test_channel_name

        # Create channel
        channel = slack_client.create_channel(name=channel_name)
        slack_cleanup.register("slack_channels", {"id": channel["id"]})

        # Set purpose
        purpose = "Test purpose from cc-plugins test suite"
        result = slack_client.set_channel_purpose(channel["id"], purpose)

        # Verify purpose was set
        assert purpose in result or result == purpose


@pytest.mark.level3
@pytest.mark.requires_credentials
class TestSlackMessageOperations:
    """Test message posting and deletion."""

    def test_post_and_delete_message(
        self,
        slack_client,
        slack_test_channel_name,
        slack_cleanup
    ):
        """Test posting and deleting a message."""
        channel_name = slack_test_channel_name

        # Create test channel
        channel = slack_client.create_channel(name=channel_name)
        slack_cleanup.register("slack_channels", {"id": channel["id"]})

        # Post message
        message = slack_client.post_message(
            channel["id"],
            "Test message from cc-plugins test suite"
        )

        assert "ts" in message
        assert message["ts"]

        # Register message for cleanup (in case delete fails)
        slack_cleanup.register("slack_messages", {
            "channel": channel["id"],
            "ts": message["ts"]
        })

        # Delete message
        result = slack_client.delete_message(channel["id"], message["ts"])
        assert result is True

        # Small delay to allow API to process
        time.sleep(0.5)

        # Verify deletion by checking messages
        messages = slack_client.get_messages(channel["id"], limit=10)
        message_timestamps = [m.get("ts") for m in messages]
        assert message["ts"] not in message_timestamps

    def test_post_message_with_blocks(
        self,
        slack_client,
        slack_test_channel_name,
        slack_cleanup
    ):
        """Test posting a message with blocks."""
        channel_name = slack_test_channel_name

        # Create test channel
        channel = slack_client.create_channel(name=channel_name)
        slack_cleanup.register("slack_channels", {"id": channel["id"]})

        # Post message with blocks
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Test Block Message*\nFrom cc-plugins test suite"
                }
            }
        ]

        message = slack_client.post_message(
            channel["id"],
            "Test message with blocks",
            blocks=blocks
        )

        slack_cleanup.register("slack_messages", {
            "channel": channel["id"],
            "ts": message["ts"]
        })

        assert "ts" in message


@pytest.mark.level3
@pytest.mark.requires_credentials
class TestSlackPinOperations:
    """Test pin operations."""

    def test_pin_and_unpin_message(
        self,
        slack_client,
        slack_test_channel_name,
        slack_cleanup
    ):
        """Test pinning and unpinning a message."""
        channel_name = slack_test_channel_name

        # Create channel and message
        channel = slack_client.create_channel(name=channel_name)
        slack_cleanup.register("slack_channels", {"id": channel["id"]})

        message = slack_client.post_message(channel["id"], "Message to pin")
        slack_cleanup.register("slack_messages", {
            "channel": channel["id"],
            "ts": message["ts"]
        })

        # Pin message
        result = slack_client.add_pin(channel["id"], message["ts"])
        assert result is True

        # Verify pin exists
        pins = slack_client.list_pins(channel["id"])
        pin_timestamps = [
            p.get("message", {}).get("ts")
            for p in pins
            if p.get("type") == "message"
        ]
        assert message["ts"] in pin_timestamps

        # Unpin
        result = slack_client.remove_pin(channel["id"], message["ts"])
        assert result is True


@pytest.mark.level3
@pytest.mark.requires_credentials
class TestSlackUserGroupOperations:
    """Test user group operations."""

    def test_create_and_disable_usergroup(
        self,
        slack_client,
        test_prefix,
        slack_cleanup
    ):
        """Test creating and disabling a user group."""
        import random
        timestamp = int(time.time())
        # Use a shorter, more unique handle (max 21 chars for Slack)
        random_suffix = random.randint(1000, 9999)
        group_name = f"Test Group {timestamp}"
        group_handle = f"cctest{timestamp % 10000000}{random_suffix}"  # Max 17 chars

        # Create usergroup
        try:
            group = slack_client.create_usergroup(
                name=group_name,
                handle=group_handle,
                description="Test usergroup from cc-plugins"
            )
        except Exception as e:
            error_str = str(e).lower()
            if "paid" in error_str or "upgrade" in error_str:
                pytest.skip("User groups require a paid Slack plan")
            if "handle_already_exists" in error_str:
                pytest.skip("Test usergroup handle already exists - run cleanup first")
            raise

        # Register for cleanup
        slack_cleanup.register("slack_usergroups", {"id": group["id"]})

        assert group["id"].startswith("S")
        assert group["handle"] == group_handle

        # Verify in list
        groups = slack_client.list_usergroups()
        group_ids = [g["id"] for g in groups]
        assert group["id"] in group_ids

        # Disable (cleanup)
        result = slack_client.disable_usergroup(group["id"])
        assert result["id"] == group["id"]


@pytest.mark.level3
@pytest.mark.requires_credentials
class TestSlackChannelCleanup:
    """Test cleanup of test channels."""

    def test_find_and_cleanup_orphaned_test_channels(
        self,
        slack_client,
        find_test_channels
    ):
        """Find any orphaned test channels from previous runs."""
        # This is a utility test to help clean up orphaned resources
        test_channels = find_test_channels()

        if test_channels:
            print(f"\nFound {len(test_channels)} orphaned test channel(s):")
            for ch in test_channels:
                print(f"  - {ch['name']} ({ch['id']})")
                if not ch.get("is_archived"):
                    try:
                        slack_client.archive_channel(ch["id"])
                        print(f"    Archived: {ch['name']}")
                    except Exception as e:
                        print(f"    Failed to archive: {e}")

        # This test always passes - it's just for cleanup
        assert True

"""
Slack plugin test fixtures.

Provides mocked and real Slack clients for all test levels.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from typing import Generator, Dict, Any
from pathlib import Path

# .testing/plugins/slack/conftest.py -> project root is 4 levels up
TESTING_ROOT = Path(__file__).parent.parent.parent  # .testing/
PROJECT_ROOT = TESTING_ROOT.parent  # cc-plugins/

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TESTING_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTING_ROOT))

# Import test helpers (from .testing/helpers/)
from helpers.mock_factory import MockClientFactory
from helpers.cleanup import cleanup_slack_resources


# ======================== MOCK FIXTURES (LEVEL 1) ========================

@pytest.fixture
def mock_slack_client():
    """Fully mocked Slack client for Level 1 tests."""
    factory = MockClientFactory()
    return factory.create_slack_client()


@pytest.fixture
def mock_slack_responses(load_mock_response):
    """Load pre-defined mock responses for Slack."""
    def _get(operation: str) -> Dict[str, Any]:
        return load_mock_response("slack", operation)
    return _get


# ======================== REAL CLIENT FIXTURES (LEVEL 2/3) ========================

@pytest.fixture(scope="module")
def slack_client(has_slack_credentials):
    """Real Slack client for Level 2 and 3 tests."""
    if not has_slack_credentials:
        pytest.skip("Slack credentials not configured")

    try:
        from slack.tool.slack_api import SlackClient
    except ImportError:
        pytest.skip("Slack SDK not available")

    return SlackClient()


@pytest.fixture
def slack_test_channel_name(test_prefix) -> str:
    """Generate a unique test channel name."""
    import time
    import random
    timestamp = int(time.time())
    random_suffix = random.randint(1000, 9999)
    # Slack channel names max 80 chars, must be lowercase
    return f"{test_prefix}ch-{timestamp}-{random_suffix}"


# ======================== CLEANUP FIXTURES (LEVEL 3) ========================

@pytest.fixture
def slack_cleanup(slack_client, cleanup_registry):
    """Cleanup fixture for Slack resources created during tests."""
    yield cleanup_registry

    # Clean up on teardown
    cleanup_slack_resources(slack_client, cleanup_registry)


# ======================== TEST HELPERS ========================

@pytest.fixture
def find_existing_channel(slack_client):
    """Helper to find an existing channel for read-only tests."""
    def _find(name_pattern: str = None) -> Dict[str, Any]:
        channels = slack_client.list_channels(limit=50)
        if name_pattern:
            for ch in channels:
                if name_pattern in ch.get("name", ""):
                    return ch
        return channels[0] if channels else None
    return _find


@pytest.fixture
def find_test_channels(slack_client, test_prefix):
    """Helper to find all test channels for cleanup."""
    def _find() -> list:
        channels = slack_client.list_channels(limit=200)
        return [ch for ch in channels if ch.get("name", "").startswith(test_prefix)]
    return _find


# ======================== EXCEPTION IMPORTS ========================

@pytest.fixture
def slack_exceptions():
    """Import Slack exception classes for testing."""
    try:
        from slack.tool.slack_api import (
            SlackError,
            SlackAuthError,
            SlackRateLimitError,
            SlackNotFoundError,
            SlackPermissionError,
        )
        return {
            "SlackError": SlackError,
            "SlackAuthError": SlackAuthError,
            "SlackRateLimitError": SlackRateLimitError,
            "SlackNotFoundError": SlackNotFoundError,
            "SlackPermissionError": SlackPermissionError,
        }
    except ImportError:
        pytest.skip("Slack module not available")

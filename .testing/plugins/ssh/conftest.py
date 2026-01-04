"""
SSH plugin test fixtures.
"""
import os
import sys
import pytest
from pathlib import Path

# .testing/plugins/ssh/conftest.py -> project root is 4 levels up
TESTING_ROOT = Path(__file__).parent.parent.parent  # .testing/
PROJECT_ROOT = TESTING_ROOT.parent  # cc-plugins/

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TESTING_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTING_ROOT))

from helpers.cleanup import cleanup_ssh_files


@pytest.fixture
def mock_ssh_client():
    """Mocked SSH client for Level 1 tests."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.exec.return_value = {"stdout": "success", "stderr": "", "exit_code": 0}
    mock.upload.return_value = True
    mock.download.return_value = True

    return mock


@pytest.fixture(scope="module")
def ssh_client(has_ssh_credentials):
    """Real SSH client for Level 2 and 3 tests."""
    if not has_ssh_credentials:
        pytest.skip("SSH credentials not configured")

    try:
        from ssh.tool.ssh_client import SSHClient
    except ImportError:
        pytest.skip("SSH client not available")

    return SSHClient()


@pytest.fixture
def ssh_cleanup(ssh_client, cleanup_registry):
    """Cleanup fixture for SSH resources."""
    yield cleanup_registry
    cleanup_ssh_files(ssh_client, cleanup_registry)


@pytest.fixture
def ssh_test_target():
    """Get SSH test target from environment."""
    target = os.getenv("SSH_TEST_TARGET")
    if not target:
        pytest.skip("SSH_TEST_TARGET not configured")
    return target

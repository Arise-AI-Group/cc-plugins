"""
SSH Plugin - Level 2 Tests (Read-Only)
"""
import pytest


@pytest.mark.level2
@pytest.mark.requires_credentials
class TestSSHReadOperations:
    """Read-only tests against real SSH connection."""

    def test_exec_read_command(self, ssh_client, ssh_test_target):
        """Test executing a read-only command."""
        result = ssh_client.exec(ssh_test_target, "whoami")

        assert result["exit_code"] == 0
        assert result["stdout"].strip()  # Should have output

    def test_exec_list_directory(self, ssh_client, ssh_test_target):
        """Test listing a directory."""
        result = ssh_client.exec(ssh_test_target, "ls -la /tmp")

        assert result["exit_code"] == 0

    def test_exec_check_disk_space(self, ssh_client, ssh_test_target):
        """Test checking disk space."""
        result = ssh_client.exec(ssh_test_target, "df -h")

        assert result["exit_code"] == 0
        assert "Filesystem" in result["stdout"] or "filesystem" in result["stdout"].lower()

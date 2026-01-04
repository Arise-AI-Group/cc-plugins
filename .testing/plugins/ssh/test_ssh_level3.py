"""
SSH Plugin - Level 3 Tests (Write Operations)
"""
import pytest
import time
import tempfile
from pathlib import Path


@pytest.mark.level3
@pytest.mark.requires_credentials
class TestSSHWriteOperations:
    """Write tests against real SSH connection."""

    def test_upload_and_delete_file(
        self,
        ssh_client,
        ssh_test_target,
        test_prefix,
        ssh_cleanup
    ):
        """Test uploading and deleting a file."""
        timestamp = int(time.time())
        remote_path = f"/tmp/{test_prefix}test-{timestamp}.txt"

        # Create local temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(f"Test content {timestamp}")
            local_path = f.name

        try:
            # Upload file
            result = ssh_client.upload(ssh_test_target, local_path, remote_path)
            assert result is True

            # Register for cleanup
            ssh_cleanup.register("ssh_files", {
                "target": ssh_test_target,
                "path": remote_path
            })

            # Verify file exists
            check = ssh_client.exec(ssh_test_target, f"cat {remote_path}")
            assert check["exit_code"] == 0
            assert str(timestamp) in check["stdout"]

            # Delete file
            delete = ssh_client.exec(ssh_test_target, f"rm {remote_path}")
            assert delete["exit_code"] == 0

        finally:
            # Clean up local file
            Path(local_path).unlink(missing_ok=True)

    def test_exec_write_command(
        self,
        ssh_client,
        ssh_test_target,
        test_prefix,
        ssh_cleanup
    ):
        """Test executing a write command."""
        timestamp = int(time.time())
        remote_path = f"/tmp/{test_prefix}mkdir-{timestamp}"

        # Register for cleanup first
        ssh_cleanup.register("ssh_files", {
            "target": ssh_test_target,
            "path": remote_path
        })

        # Create directory
        result = ssh_client.exec(ssh_test_target, f"mkdir -p {remote_path}")
        assert result["exit_code"] == 0

        # Verify directory exists
        check = ssh_client.exec(ssh_test_target, f"test -d {remote_path} && echo exists")
        assert "exists" in check["stdout"]

        # Cleanup
        ssh_client.exec(ssh_test_target, f"rmdir {remote_path}")

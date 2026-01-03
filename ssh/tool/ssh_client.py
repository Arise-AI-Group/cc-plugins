#!/usr/bin/env python3
"""
SSH Client Tool

Execute commands and transfer files on remote servers via SSH/SFTP.

Usage (CLI):
    ./run tool/ssh_client.py exec user@host "command"
    ./run tool/ssh_client.py exec user@host:port "command"

    ./run tool/ssh_client.py upload user@host local_path remote_path
    ./run tool/ssh_client.py download user@host remote_path local_path

Usage (Module):
    from tool.ssh_client import SSHClient
    client = SSHClient()
    stdout, stderr, code = client.exec("root@192.168.1.50", "ls -la")
    client.upload("root@server", "local.txt", "/tmp/remote.txt")
    client.download("root@server", "/var/log/syslog", "./syslog")
"""

import sys
import os
import stat
import argparse
from pathlib import Path
from typing import Tuple, Optional

try:
    import paramiko
except ImportError:
    print("Error: paramiko not installed. Run: pip install paramiko", file=sys.stderr)
    sys.exit(1)

from .config import get_api_key

SSH_KEY_PATH = get_api_key("SSH_KEY_PATH")
SSH_PASSWORD = get_api_key("SSH_PASSWORD")


# --- Custom Exceptions ---

class SSHError(Exception):
    """Base exception for SSH errors."""
    pass


class SSHAuthError(SSHError):
    """Authentication failed."""
    pass


class SSHConnectionError(SSHError):
    """Connection failed."""
    pass


class SSHFileError(SSHError):
    """File transfer error."""
    pass


# --- SSH Client ---

class SSHClient:
    """Client for SSH command execution and file transfer."""

    def __init__(self, key_path: str = None, password: str = None):
        """
        Initialize SSH client.

        Args:
            key_path: Path to SSH private key (default: SSH_KEY_PATH env var)
            password: SSH password (default: SSH_PASSWORD env var)
        """
        self.key_path = key_path or SSH_KEY_PATH
        self.password = password or SSH_PASSWORD

        if not self.key_path and not self.password:
            raise ValueError(
                "No SSH credentials configured. "
                "Set SSH_KEY_PATH or SSH_PASSWORD in .env file."
            )

    def _parse_target(self, target: str) -> Tuple[str, str, int]:
        """
        Parse target string into user, host, port.

        Args:
            target: Format "user@host" or "user@host:port"

        Returns:
            Tuple of (user, host, port)
        """
        if "@" not in target:
            raise ValueError(f"Invalid target format: {target}. Expected user@host[:port]")

        user, hostport = target.split("@", 1)

        if ":" in hostport:
            host, port_str = hostport.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                raise ValueError(f"Invalid port: {port_str}")
        else:
            host = hostport
            port = 22

        return user, host, port

    def _connect(self, target: str) -> paramiko.SSHClient:
        """
        Establish SSH connection to target.

        Args:
            target: Target in format "user@host[:port]"

        Returns:
            Connected paramiko.SSHClient
        """
        user, host, port = self._parse_target(target)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # Try key-based auth first
            if self.key_path and os.path.exists(self.key_path):
                try:
                    client.connect(
                        hostname=host,
                        port=port,
                        username=user,
                        key_filename=self.key_path,
                        timeout=30
                    )
                    return client
                except paramiko.AuthenticationException:
                    # Fall through to password auth
                    pass

            # Try password auth
            if self.password:
                client.connect(
                    hostname=host,
                    port=port,
                    username=user,
                    password=self.password,
                    timeout=30
                )
                return client

            raise SSHAuthError(
                f"Authentication failed for {user}@{host}. "
                "Check SSH_KEY_PATH or SSH_PASSWORD."
            )

        except paramiko.AuthenticationException as e:
            raise SSHAuthError(f"Authentication failed: {e}")
        except paramiko.SSHException as e:
            raise SSHConnectionError(f"SSH error: {e}")
        except OSError as e:
            raise SSHConnectionError(f"Connection failed to {host}:{port}: {e}")

    def exec(self, target: str, command: str) -> Tuple[str, str, int]:
        """
        Execute command on remote server.

        Args:
            target: Target in format "user@host[:port]"
            command: Command to execute

        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        client = self._connect(target)
        try:
            stdin, stdout, stderr = client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()

            stdout_str = stdout.read().decode("utf-8", errors="replace")
            stderr_str = stderr.read().decode("utf-8", errors="replace")

            return stdout_str, stderr_str, exit_code
        finally:
            client.close()

    def upload(self, target: str, local_path: str, remote_path: str) -> None:
        """
        Upload file or directory to remote server.

        Args:
            target: Target in format "user@host[:port]"
            local_path: Local file or directory path
            remote_path: Remote destination path
        """
        if not os.path.exists(local_path):
            raise SSHFileError(f"Local path not found: {local_path}")

        client = self._connect(target)
        try:
            sftp = client.open_sftp()
            try:
                if os.path.isdir(local_path):
                    self._upload_dir(sftp, local_path, remote_path)
                else:
                    self._ensure_remote_dir(sftp, os.path.dirname(remote_path))
                    sftp.put(local_path, remote_path)
            finally:
                sftp.close()
        finally:
            client.close()

    def _upload_dir(self, sftp: paramiko.SFTPClient, local_dir: str, remote_dir: str) -> None:
        """Recursively upload directory."""
        self._ensure_remote_dir(sftp, remote_dir)

        for item in os.listdir(local_dir):
            local_item = os.path.join(local_dir, item)
            remote_item = f"{remote_dir}/{item}"

            if os.path.isdir(local_item):
                self._upload_dir(sftp, local_item, remote_item)
            else:
                sftp.put(local_item, remote_item)

    def _ensure_remote_dir(self, sftp: paramiko.SFTPClient, remote_dir: str) -> None:
        """Ensure remote directory exists."""
        if not remote_dir or remote_dir == "/":
            return

        dirs = []
        path = remote_dir
        while path and path != "/":
            dirs.append(path)
            path = os.path.dirname(path)

        for d in reversed(dirs):
            try:
                sftp.stat(d)
            except FileNotFoundError:
                sftp.mkdir(d)

    def download(self, target: str, remote_path: str, local_path: str) -> None:
        """
        Download file or directory from remote server.

        Args:
            target: Target in format "user@host[:port]"
            remote_path: Remote file or directory path
            local_path: Local destination path
        """
        client = self._connect(target)
        try:
            sftp = client.open_sftp()
            try:
                # Check if remote path is a directory
                try:
                    remote_stat = sftp.stat(remote_path)
                    is_dir = stat.S_ISDIR(remote_stat.st_mode)
                except FileNotFoundError:
                    raise SSHFileError(f"Remote path not found: {remote_path}")

                if is_dir:
                    self._download_dir(sftp, remote_path, local_path)
                else:
                    # Ensure local directory exists
                    local_dir = os.path.dirname(local_path)
                    if local_dir:
                        os.makedirs(local_dir, exist_ok=True)
                    sftp.get(remote_path, local_path)
            finally:
                sftp.close()
        finally:
            client.close()

    def _download_dir(self, sftp: paramiko.SFTPClient, remote_dir: str, local_dir: str) -> None:
        """Recursively download directory."""
        os.makedirs(local_dir, exist_ok=True)

        for item in sftp.listdir_attr(remote_dir):
            remote_item = f"{remote_dir}/{item.filename}"
            local_item = os.path.join(local_dir, item.filename)

            if stat.S_ISDIR(item.st_mode):
                self._download_dir(sftp, remote_item, local_item)
            else:
                sftp.get(remote_item, local_item)


# --- CLI Interface ---

def cmd_exec(args):
    """Execute command on remote server."""
    client = SSHClient()
    stdout, stderr, exit_code = client.exec(args.target, args.command)

    if stdout:
        print(stdout, end="")
        sys.stdout.flush()
    if stderr:
        print(stderr, end="", file=sys.stderr)
        sys.stderr.flush()

    return exit_code


def cmd_upload(args):
    """Upload file to remote server."""
    client = SSHClient()
    client.upload(args.target, args.local_path, args.remote_path)
    print(f"Uploaded: {args.local_path} -> {args.target}:{args.remote_path}")
    return 0


def cmd_download(args):
    """Download file from remote server."""
    client = SSHClient()
    client.download(args.target, args.remote_path, args.local_path)
    print(f"Downloaded: {args.target}:{args.remote_path} -> {args.local_path}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="SSH client for remote command execution and file transfer"
    )
    subparsers = parser.add_subparsers(dest="action", help="Command")

    # exec command
    exec_parser = subparsers.add_parser("exec", help="Execute command on remote server")
    exec_parser.add_argument("target", help="Target: user@host[:port]")
    exec_parser.add_argument("command", help="Command to execute")

    # upload command
    upload_parser = subparsers.add_parser("upload", help="Upload file to remote server")
    upload_parser.add_argument("target", help="Target: user@host[:port]")
    upload_parser.add_argument("local_path", help="Local file or directory path")
    upload_parser.add_argument("remote_path", help="Remote destination path")

    # download command
    download_parser = subparsers.add_parser("download", help="Download file from remote server")
    download_parser.add_argument("target", help="Target: user@host[:port]")
    download_parser.add_argument("remote_path", help="Remote file or directory path")
    download_parser.add_argument("local_path", help="Local destination path")

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        return 0

    try:
        if args.action == "exec":
            return cmd_exec(args)
        elif args.action == "upload":
            return cmd_upload(args)
        elif args.action == "download":
            return cmd_download(args)
    except SSHAuthError as e:
        print(f"Authentication error: {e}", file=sys.stderr)
        return 1
    except SSHConnectionError as e:
        print(f"Connection error: {e}", file=sys.stderr)
        return 1
    except SSHFileError as e:
        print(f"File error: {e}", file=sys.stderr)
        return 1
    except SSHError as e:
        print(f"SSH error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)

#!/usr/bin/env python3
"""ActivityWatch Process Watcher — tracks apps after they lose window focus.

Unlike aw-watcher-window (which only tracks the focused window), this daemon
registers every app that gains focus and continues tracking it in the background
until the process exits. This reveals parallel work: builds running while coding,
downloads while browsing, etc.

Registration flow:
  1. Poll every N seconds for the frontmost app (via osascript + psutil)
  2. Register its PID when it first gains focus
  3. After it loses focus, send heartbeats to AW while the PID is still alive
  4. Stop tracking when the process exits

Usage:
  ./run tool/process_watcher.py start            # foreground
  ./run tool/process_watcher.py start --daemon    # background
  ./run tool/process_watcher.py stop              # stop background daemon
  ./run tool/process_watcher.py status            # show tracked processes
  ./run tool/process_watcher.py install           # install macOS LaunchAgent
"""

import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

IGNORE_APPS = {
    "loginwindow", "Dock", "SystemUIServer", "Finder", "Spotlight",
    "Control Center", "Notification Center", "WindowManager",
    "universalAccessAuthWarn", "ScreenSaverEngine", "SecurityAgent",
    "UserNotificationCenter", "AirPlayUIAgent", "TextInputMenuAgent",
    "CoreServicesUIAgent", "WiFiAgent",
}

PID_FILE = Path.home() / ".config" / "cc-plugins" / "aw-process-watcher.pid"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE = "%H:%M:%S"

log = logging.getLogger("aw-process-watcher")


# ---------------------------------------------------------------------------
# macOS frontmost app detection
# ---------------------------------------------------------------------------

def get_frontmost_app() -> dict | None:
    """Get the currently focused app name and PID on macOS."""
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of '
             'first application process whose frontmost is true'],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode != 0:
            return None
        app_name = result.stdout.strip()
        if not app_name:
            return None

        # Find the PID via psutil
        pid = None
        for proc in psutil.process_iter(["pid", "name"]):
            if proc.info["name"] == app_name:
                pid = proc.info["pid"]
                break

        if pid is None:
            return None

        return {"app": app_name, "pid": pid}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Process Watcher
# ---------------------------------------------------------------------------

class ProcessWatcher:
    """Tracks apps after they lose window focus via AW heartbeats."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5600,
        poll_interval: int = 5,
    ):
        self.api_url = f"http://{host}:{port}/api/0"
        self.poll_interval = poll_interval
        self.pulsetime = poll_interval + 5
        self.hostname = socket.gethostname()
        self.bucket_id = f"aw-watcher-process_{self.hostname}"

        # pid -> {app, registered_at}
        self.tracked: dict[int, dict] = {}
        self.current_focus_pid: int | None = None
        self._running = True

    def _ensure_bucket(self) -> bool:
        """Create the AW bucket if it doesn't exist."""
        try:
            resp = requests.post(
                f"{self.api_url}/buckets/{self.bucket_id}",
                json={
                    "client": "aw-watcher-process",
                    "type": "app.process.background",
                    "hostname": self.hostname,
                },
                timeout=5,
            )
            # 200 = created, 304 = already exists — both are fine
            return resp.status_code in (200, 304)
        except requests.ConnectionError:
            log.error("Cannot connect to ActivityWatch at %s", self.api_url)
            return False

    def _heartbeat(self, data: dict) -> None:
        """Send a heartbeat event to the AW bucket."""
        try:
            requests.post(
                f"{self.api_url}/buckets/{self.bucket_id}/heartbeat"
                f"?pulsetime={self.pulsetime}",
                json={
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "duration": 0,
                    "data": data,
                },
                timeout=3,
            )
        except requests.ConnectionError:
            pass  # AW server temporarily unavailable — skip this beat

    def poll(self) -> None:
        """Single poll cycle: register focused app, heartbeat background PIDs."""
        front = get_frontmost_app()

        if front and front["app"] not in IGNORE_APPS:
            pid = front["pid"]
            self.current_focus_pid = pid

            # Register if new
            if pid not in self.tracked:
                self.tracked[pid] = {
                    "app": front["app"],
                    "registered_at": datetime.now(timezone.utc).isoformat(),
                }
                log.info("Registered: %s (PID %d)", front["app"], pid)
        else:
            self.current_focus_pid = None

        # Heartbeat for all tracked background PIDs
        dead_pids = []
        for pid, info in self.tracked.items():
            if pid == self.current_focus_pid:
                continue  # skip the currently focused app

            try:
                proc = psutil.Process(pid)
                if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                    dead_pids.append(pid)
                    continue

                self._heartbeat({
                    "app": info["app"],
                    "pid": pid,
                    "status": "background",
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                dead_pids.append(pid)

        # Clean up dead processes
        for pid in dead_pids:
            app = self.tracked[pid]["app"]
            del self.tracked[pid]
            log.info("Unregistered: %s (PID %d) — process exited", app, pid)

    def run(self) -> None:
        """Main loop — poll until stopped."""
        if not self._ensure_bucket():
            log.error("Failed to create AW bucket. Is ActivityWatch running?")
            sys.exit(1)

        log.info(
            "Process watcher started (poll=%ds, bucket=%s)",
            self.poll_interval, self.bucket_id,
        )

        def handle_signal(sig, _frame):
            log.info("Received signal %d, shutting down...", sig)
            self._running = False

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        while self._running:
            try:
                self.poll()
            except Exception as e:
                log.error("Poll error: %s", e)
            time.sleep(self.poll_interval)

        log.info("Process watcher stopped. Tracked %d apps.", len(self.tracked))

    def status_report(self) -> dict:
        """Return current tracking status."""
        return {
            "running": self._running,
            "bucket_id": self.bucket_id,
            "tracked_count": len(self.tracked),
            "tracked": {
                pid: info for pid, info in self.tracked.items()
            },
            "current_focus_pid": self.current_focus_pid,
        }


# ---------------------------------------------------------------------------
# Daemon management
# ---------------------------------------------------------------------------

def write_pid_file() -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def read_pid_file() -> int | None:
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except ValueError:
            pass
    return None


def remove_pid_file() -> None:
    if PID_FILE.exists():
        PID_FILE.unlink()


def is_daemon_running() -> tuple[bool, int | None]:
    pid = read_pid_file()
    if pid and psutil.pid_exists(pid):
        try:
            proc = psutil.Process(pid)
            if "process_watcher" in " ".join(proc.cmdline()):
                return True, pid
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False, pid


def daemonize() -> None:
    """Fork into background."""
    pid = os.fork()
    if pid > 0:
        # Parent — exit
        sys.exit(0)

    os.setsid()
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    # Redirect stdio
    sys.stdin = open(os.devnull, "r")
    log_path = Path.home() / ".config" / "cc-plugins" / "aw-process-watcher.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "a")
    sys.stdout = log_file
    sys.stderr = log_file


# ---------------------------------------------------------------------------
# LaunchAgent
# ---------------------------------------------------------------------------

LAUNCHAGENT_LABEL = "com.arise.aw-process-watcher"


def install_launchagent(run_script: str) -> str:
    """Generate and install a macOS LaunchAgent plist."""
    plist_dir = Path.home() / "Library" / "LaunchAgents"
    plist_dir.mkdir(parents=True, exist_ok=True)
    plist_path = plist_dir / f"{LAUNCHAGENT_LABEL}.plist"

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LAUNCHAGENT_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{run_script}</string>
        <string>tool/process_watcher.py</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{Path.home()}/.config/cc-plugins/aw-process-watcher.log</string>
    <key>StandardErrorPath</key>
    <string>{Path.home()}/.config/cc-plugins/aw-process-watcher.log</string>
</dict>
</plist>"""

    plist_path.write_text(plist)
    return str(plist_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ActivityWatch process watcher daemon"
    )
    sub = parser.add_subparsers(dest="command")

    start_p = sub.add_parser("start", help="Start the watcher")
    start_p.add_argument("--daemon", "-d", action="store_true",
                         help="Run in background")
    start_p.add_argument("--poll", type=int, default=5,
                         help="Poll interval in seconds (default: 5)")
    start_p.add_argument("--host", default="localhost")
    start_p.add_argument("--port", type=int, default=5600)

    sub.add_parser("stop", help="Stop the background daemon")
    sub.add_parser("status", help="Check if the watcher is running")
    sub.add_parser("install", help="Install macOS LaunchAgent for auto-start")
    sub.add_parser("uninstall", help="Remove macOS LaunchAgent")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "start":
        running, old_pid = is_daemon_running()
        if running:
            print(f"Already running (PID {old_pid}). Use 'stop' first.")
            return

        if args.daemon:
            print("Starting process watcher in background...")
            daemonize()

        logging.basicConfig(
            level=logging.INFO, format=LOG_FORMAT, datefmt=LOG_DATE,
        )
        write_pid_file()
        try:
            watcher = ProcessWatcher(
                host=args.host, port=args.port,
                poll_interval=args.poll,
            )
            watcher.run()
        finally:
            remove_pid_file()

    elif args.command == "stop":
        running, pid = is_daemon_running()
        if not running:
            print("Process watcher is not running.")
            remove_pid_file()
            return
        os.kill(pid, signal.SIGTERM)
        # Wait for it to exit
        for _ in range(20):
            if not psutil.pid_exists(pid):
                break
            time.sleep(0.25)
        remove_pid_file()
        print(f"Stopped process watcher (PID {pid}).")

    elif args.command == "status":
        running, pid = is_daemon_running()
        if running:
            print(f"Running (PID {pid})")
            # Show tracked processes by reading the AW bucket
            try:
                from .config import get_api_key
                host = get_api_key("ACTIVITYWATCH_HOST", "localhost")
                port = get_api_key("ACTIVITYWATCH_PORT", "5600")
            except Exception:
                host, port = "localhost", "5600"
            api_url = f"http://{host}:{port}/api/0"
            hostname = socket.gethostname()
            bucket_id = f"aw-watcher-process_{hostname}"
            try:
                resp = requests.get(
                    f"{api_url}/buckets/{bucket_id}/events",
                    params={"limit": 10}, timeout=3,
                )
                if resp.ok:
                    events = resp.json()
                    if events:
                        print(f"\nRecent background events ({len(events)}):")
                        for ev in events[:10]:
                            data = ev.get("data", {})
                            dur = ev.get("duration", 0)
                            print(f"  {data.get('app', '?'):20s}  "
                                  f"PID {data.get('pid', '?'):>6}  "
                                  f"{dur:.0f}s")
                    else:
                        print("No background events recorded yet.")
            except Exception:
                print("(Cannot query AW for event details)")
        else:
            print("Not running.")

    elif args.command == "install":
        script_dir = Path(__file__).resolve().parent.parent
        run_script = str(script_dir / "run")
        plist_path = install_launchagent(run_script)
        print(f"LaunchAgent installed: {plist_path}")
        print(f"To load now: launchctl load {plist_path}")
        print(f"It will auto-start on login.")

    elif args.command == "uninstall":
        plist_path = (Path.home() / "Library" / "LaunchAgents"
                      / f"{LAUNCHAGENT_LABEL}.plist")
        if plist_path.exists():
            subprocess.run(
                ["launchctl", "unload", str(plist_path)],
                capture_output=True,
            )
            plist_path.unlink()
            print("LaunchAgent removed.")
        else:
            print("LaunchAgent not installed.")

        running, pid = is_daemon_running()
        if running:
            os.kill(pid, signal.SIGTERM)
            remove_pid_file()
            print(f"Stopped running daemon (PID {pid}).")


if __name__ == "__main__":
    main()

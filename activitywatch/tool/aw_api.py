#!/usr/bin/env python3
"""ActivityWatch API client — SQLite-powered time analysis and reporting.

Reads directly from the ActivityWatch SQLite database for fast, expressive
analysis. Uses REST API only for live queries (current activity).
"""

import argparse
import json
import os
import platform
import re
import sqlite3
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

from .config import get_api_key


def _date_to_ts(d: str) -> str:
    """Convert a date or datetime string to DB-compatible timestamp format.

    The AW database uses space-separated timestamps (2026-02-07 00:00:00)
    not ISO T-separated (2026-02-07T00:00:00). SQLite string comparison
    requires matching format.
    """
    return d.replace("T", " ")


def _utc_to_local(ts_str: str) -> datetime:
    """Convert a UTC timestamp string from the AW database to a local datetime."""
    from datetime import timezone as tz
    clean = ts_str.replace("+00:00", "").replace("Z", "").strip()
    utc_dt = datetime.fromisoformat(clean).replace(tzinfo=tz.utc)
    return utc_dt.astimezone(tz=None)  # system local timezone


# ---------------------------------------------------------------------------
# Database discovery
# ---------------------------------------------------------------------------

def find_db_path() -> Path:
    """Locate the ActivityWatch SQLite database (platform-aware)."""
    override = get_api_key("ACTIVITYWATCH_DB_PATH")
    if override:
        p = Path(override).expanduser()
        if p.exists():
            return p
        raise FileNotFoundError(f"ACTIVITYWATCH_DB_PATH does not exist: {p}")

    system = platform.system()
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "activitywatch"
    elif system == "Linux":
        xdg = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        base = Path(xdg) / "activitywatch"
    elif system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", "")) / "activitywatch" / "activitywatch"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

    # Try aw-server (Python) then aw-server-rust
    for server_dir in ["aw-server", "aw-server-rust"]:
        for db_name in ["peewee-sqlite.v2.db", "sqlite.db"]:
            candidate = base / server_dir / db_name
            if candidate.exists():
                return candidate

    raise FileNotFoundError(
        f"ActivityWatch database not found in {base}. "
        "Is ActivityWatch installed and has it been run at least once?"
    )


# ---------------------------------------------------------------------------
# Core client
# ---------------------------------------------------------------------------

class ActivityWatchAPI:
    """High-level ActivityWatch client backed by direct SQLite access."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or find_db_path()
        host = get_api_key("ACTIVITYWATCH_HOST", "localhost")
        port = get_api_key("ACTIVITYWATCH_PORT", "5600")
        self.api_url = f"http://{host}:{port}/api/0"
        self._config_path = Path.home() / ".config" / "cc-plugins" / "activitywatch.json"

    # --- low-level DB helpers ------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """Open a read-only connection to the AW database."""
        uri = f"file:{self.db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def _query(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute SQL and return list of dicts."""
        conn = self._connect()
        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- bucket helpers ------------------------------------------------------

    def list_buckets(self, type_filter: Optional[str] = None) -> list[dict]:
        """List all buckets with event counts and date ranges."""
        sql = """
            SELECT b.id, b.type, b.client, b.hostname, b.created,
                   COUNT(e.id) as event_count,
                   MIN(e.timestamp) as first_event,
                   MAX(e.timestamp) as last_event
            FROM bucketmodel b
            LEFT JOIN eventmodel e ON e.bucket_id = b.key
        """
        params: tuple = ()
        if type_filter:
            sql += " WHERE b.type = ?"
            params = (type_filter,)
        sql += " GROUP BY b.key ORDER BY b.created DESC"
        return self._query(sql, params)

    def get_bucket_info(self, bucket_id: str) -> dict:
        """Get detailed info for a specific bucket."""
        buckets = self._query("""
            SELECT b.id, b.type, b.client, b.hostname, b.created,
                   COUNT(e.id) as event_count,
                   MIN(e.timestamp) as first_event,
                   MAX(e.timestamp) as last_event,
                   SUM(e.duration) as total_duration
            FROM bucketmodel b
            LEFT JOIN eventmodel e ON e.bucket_id = b.key
            WHERE b.id = ?
            GROUP BY b.key
        """, (bucket_id,))
        if not buckets:
            raise ValueError(f"Bucket not found: {bucket_id}")
        info = buckets[0]
        # Add sample events
        info["sample_events"] = self._query("""
            SELECT e.timestamp, e.duration, e.datastr
            FROM eventmodel e JOIN bucketmodel b ON e.bucket_id = b.key
            WHERE b.id = ? ORDER BY e.timestamp DESC LIMIT 5
        """, (bucket_id,))
        for ev in info["sample_events"]:
            ev["data"] = json.loads(ev.pop("datastr"))
        return info

    def _bucket_ids_by_type(self, bucket_type: str) -> list[str]:
        """Get all bucket IDs matching a type."""
        rows = self._query(
            "SELECT id FROM bucketmodel WHERE type = ?", (bucket_type,)
        )
        return [r["id"] for r in rows]

    def window_buckets(self) -> list[str]:
        return self._bucket_ids_by_type("currentwindow")

    def afk_buckets(self) -> list[str]:
        return self._bucket_ids_by_type("afkstatus")

    def vscode_buckets(self) -> list[str]:
        return self._bucket_ids_by_type("app.editor.activity")

    def browser_buckets(self) -> list[str]:
        return self._bucket_ids_by_type("web.tab.current")

    # --- event retrieval -----------------------------------------------------

    def get_events(
        self,
        bucket_id: str,
        limit: int = 100,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> list[dict]:
        """Get raw events from a bucket with optional date filtering."""
        sql = """
            SELECT e.id, e.timestamp, e.duration, e.datastr
            FROM eventmodel e JOIN bucketmodel b ON e.bucket_id = b.key
            WHERE b.id = ?
        """
        params: list = [bucket_id]
        if start:
            sql += " AND e.timestamp >= ?"
            params.append(_date_to_ts(start))
        if end:
            sql += " AND e.timestamp < ?"
            params.append(_date_to_ts(end))
        sql += " ORDER BY e.timestamp DESC LIMIT ?"
        params.append(limit)
        events = self._query(sql, tuple(params))
        for ev in events:
            ev["data"] = json.loads(ev.pop("datastr"))
        return events

    def get_current_activity(self) -> dict:
        """Get current window and AFK status via REST API (live data)."""
        import requests

        result = {}
        try:
            resp = requests.get(f"{self.api_url}/buckets/", timeout=3)
            resp.raise_for_status()
            buckets = resp.json()

            for bid in buckets:
                if "watcher-window" in bid:
                    events = requests.get(
                        f"{self.api_url}/buckets/{bid}/events",
                        params={"limit": 1}, timeout=3
                    ).json()
                    if events:
                        result["window"] = {
                            "app": events[0].get("data", {}).get("app"),
                            "title": events[0].get("data", {}).get("title"),
                            "timestamp": events[0].get("timestamp"),
                        }
                    break

            for bid in buckets:
                if "watcher-afk" in bid:
                    events = requests.get(
                        f"{self.api_url}/buckets/{bid}/events",
                        params={"limit": 1}, timeout=3
                    ).json()
                    if events:
                        result["afk"] = {
                            "status": events[0].get("data", {}).get("status"),
                            "since": events[0].get("timestamp"),
                            "duration_seconds": events[0].get("duration", 0),
                        }
                    break
        except Exception as e:
            result["error"] = f"ActivityWatch server not reachable: {e}"
        return result

    def get_server_info(self) -> dict:
        """Get summary of database contents."""
        buckets = self.list_buckets()
        total_events = sum(b["event_count"] for b in buckets)
        hostnames = list({b["hostname"] for b in buckets})
        return {
            "db_path": str(self.db_path),
            "total_buckets": len(buckets),
            "total_events": total_events,
            "hostnames": hostnames,
            "buckets": [
                {"id": b["id"], "type": b["type"], "events": b["event_count"]}
                for b in buckets
            ],
        }

    # --- time analysis (SQL-powered) -----------------------------------------

    def _afk_cte(self, start: str, end: str) -> str:
        """Common Table Expression for not-afk periods across all hostnames."""
        s, e = _date_to_ts(start), _date_to_ts(end)
        return f"""
        afk_periods AS (
            SELECT e.timestamp as afk_start,
                   datetime(e.timestamp, '+' || CAST(e.duration AS INTEGER) || ' seconds') as afk_end
            FROM eventmodel e
            JOIN bucketmodel b ON e.bucket_id = b.key
            WHERE b.type = 'afkstatus'
              AND json_extract(e.datastr, '$.status') = 'not-afk'
              AND e.duration > 0
              AND e.timestamp >= '{s}'
              AND e.timestamp < '{e}'
        )"""

    def time_by_app(
        self,
        start: str,
        end: str,
        afk_filtered: bool = True,
        limit: int = 50,
    ) -> list[dict]:
        """Aggregate active time by application."""
        s, e = _date_to_ts(start), _date_to_ts(end)
        if afk_filtered:
            sql = f"""
                WITH {self._afk_cte(start, end)}
                SELECT json_extract(w.datastr, '$.app') as app,
                       SUM(
                           (MIN(julianday(a.afk_end),
                                julianday(datetime(w.timestamp, '+' || CAST(w.duration AS INTEGER) || ' seconds')))
                            - MAX(julianday(w.timestamp), julianday(a.afk_start))
                           ) * 86400
                       ) as seconds
                FROM eventmodel w
                JOIN bucketmodel wb ON w.bucket_id = wb.key
                JOIN afk_periods a
                  ON w.timestamp < a.afk_end
                  AND datetime(w.timestamp, '+' || CAST(w.duration AS INTEGER) || ' seconds') > a.afk_start
                WHERE wb.type = 'currentwindow'
                  AND w.duration > 0
                  AND w.timestamp >= ?
                  AND w.timestamp < ?
                GROUP BY app
                HAVING seconds > 0
                ORDER BY seconds DESC
                LIMIT ?
            """
        else:
            sql = """
                SELECT json_extract(e.datastr, '$.app') as app,
                       SUM(e.duration) as seconds
                FROM eventmodel e
                JOIN bucketmodel b ON e.bucket_id = b.key
                WHERE b.type = 'currentwindow'
                  AND e.duration > 0
                  AND e.timestamp >= ?
                  AND e.timestamp < ?
                GROUP BY app
                ORDER BY seconds DESC
                LIMIT ?
            """
        rows = self._query(sql, (s, e, limit))
        for r in rows:
            r["formatted"] = self.format_duration(r["seconds"])
        return rows

    def time_by_title(
        self,
        start: str,
        end: str,
        app: Optional[str] = None,
        afk_filtered: bool = True,
        limit: int = 30,
    ) -> list[dict]:
        """Aggregate time by window title, optionally filtered to an app."""
        s, e = _date_to_ts(start), _date_to_ts(end)
        if afk_filtered:
            app_clause = ""
            if app:
                app_clause = f"AND LOWER(json_extract(w.datastr, '$.app')) = LOWER('{app}')"
            sql = f"""
                WITH {self._afk_cte(start, end)}
                SELECT json_extract(w.datastr, '$.app') as app,
                       json_extract(w.datastr, '$.title') as title,
                       SUM(
                           (MIN(julianday(a.afk_end),
                                julianday(datetime(w.timestamp, '+' || CAST(w.duration AS INTEGER) || ' seconds')))
                            - MAX(julianday(w.timestamp), julianday(a.afk_start))
                           ) * 86400
                       ) as seconds
                FROM eventmodel w
                JOIN bucketmodel wb ON w.bucket_id = wb.key
                JOIN afk_periods a
                  ON w.timestamp < a.afk_end
                  AND datetime(w.timestamp, '+' || CAST(w.duration AS INTEGER) || ' seconds') > a.afk_start
                WHERE wb.type = 'currentwindow'
                  AND w.duration > 0
                  AND w.timestamp >= ?
                  AND w.timestamp < ?
                  {app_clause}
                GROUP BY app, title
                HAVING seconds > 0
                ORDER BY seconds DESC
                LIMIT ?
            """
        else:
            app_clause = ""
            if app:
                app_clause = f"AND LOWER(json_extract(e.datastr, '$.app')) = LOWER('{app}')"
            sql = f"""
                SELECT json_extract(e.datastr, '$.app') as app,
                       json_extract(e.datastr, '$.title') as title,
                       SUM(e.duration) as seconds
                FROM eventmodel e
                JOIN bucketmodel b ON e.bucket_id = b.key
                WHERE b.type = 'currentwindow'
                  AND e.duration > 0
                  AND e.timestamp >= ?
                  AND e.timestamp < ?
                  {app_clause}
                GROUP BY app, title
                ORDER BY seconds DESC
                LIMIT ?
            """
        rows = self._query(sql, (s, e, limit))
        for r in rows:
            r["formatted"] = self.format_duration(r["seconds"])
        return rows

    def active_time(self, start: str, end: str) -> dict:
        """Calculate total active vs AFK time."""
        s, e = _date_to_ts(start), _date_to_ts(end)
        rows = self._query("""
            SELECT json_extract(e.datastr, '$.status') as status,
                   SUM(e.duration) as seconds
            FROM eventmodel e
            JOIN bucketmodel b ON e.bucket_id = b.key
            WHERE b.type = 'afkstatus'
              AND e.timestamp >= ?
              AND e.timestamp < ?
            GROUP BY status
        """, (s, e))
        result = {"active_seconds": 0, "afk_seconds": 0}
        for r in rows:
            if r["status"] == "not-afk":
                result["active_seconds"] = r["seconds"]
            else:
                result["afk_seconds"] = r["seconds"]
        result["active_formatted"] = self.format_duration(result["active_seconds"])
        result["afk_formatted"] = self.format_duration(result["afk_seconds"])
        total = result["active_seconds"] + result["afk_seconds"]
        result["active_pct"] = round(result["active_seconds"] / total * 100, 1) if total else 0
        return result

    def daily_summary(self, target_date: Optional[str] = None) -> dict:
        """Generate a complete summary for a single day."""
        if not target_date:
            target_date = date.today().isoformat()
        start = f"{target_date} 00:00:00"
        end_date = date.fromisoformat(target_date) + timedelta(days=1)
        end = f"{end_date.isoformat()} 00:00:00"

        return {
            "date": target_date,
            "active_time": self.active_time(start, end),
            "top_apps": self.time_by_app(start, end, limit=15),
            "top_titles": self.time_by_title(start, end, limit=15),
            "editor_activity": self.editor_activity(start, end),
        }

    def range_summary(
        self,
        start: str,
        end: str,
        group_by: str = "day",
    ) -> list[dict]:
        """Aggregate time over a date range, grouped by day or app."""
        if group_by == "day":
            s, e = _date_to_ts(start), _date_to_ts(end)
            sql = f"""
                WITH {self._afk_cte(start, end)}
                SELECT DATE(w.timestamp, 'localtime') as day,
                       SUM(
                           (MIN(julianday(a.afk_end),
                                julianday(datetime(w.timestamp, '+' || CAST(w.duration AS INTEGER) || ' seconds')))
                            - MAX(julianday(w.timestamp), julianday(a.afk_start))
                           ) * 86400
                       ) as seconds
                FROM eventmodel w
                JOIN bucketmodel wb ON w.bucket_id = wb.key
                JOIN afk_periods a
                  ON w.timestamp < a.afk_end
                  AND datetime(w.timestamp, '+' || CAST(w.duration AS INTEGER) || ' seconds') > a.afk_start
                WHERE wb.type = 'currentwindow'
                  AND w.duration > 0
                  AND w.timestamp >= ?
                  AND w.timestamp < ?
                GROUP BY day
                HAVING seconds > 0
                ORDER BY day
            """
            rows = self._query(sql, (s, e))
        elif group_by == "app":
            rows = self.time_by_app(start, end, limit=100)
        else:
            raise ValueError(f"Invalid group_by: {group_by}. Use 'day' or 'app'.")

        for r in rows:
            r["formatted"] = self.format_duration(r["seconds"])
        return rows

    def find_focus_sessions(
        self,
        start: str,
        end: str,
        min_minutes: int = 30,
    ) -> list[dict]:
        """Find sustained active (not-afk) periods."""
        min_seconds = min_minutes * 60
        s, e = _date_to_ts(start), _date_to_ts(end)
        rows = self._query("""
            SELECT e.timestamp as session_start,
                   datetime(e.timestamp, '+' || CAST(e.duration AS INTEGER) || ' seconds') as session_end,
                   e.duration as seconds
            FROM eventmodel e
            JOIN bucketmodel b ON e.bucket_id = b.key
            WHERE b.type = 'afkstatus'
              AND json_extract(e.datastr, '$.status') = 'not-afk'
              AND e.duration >= ?
              AND e.timestamp >= ?
              AND e.timestamp < ?
            ORDER BY e.timestamp
        """, (min_seconds, s, e))
        for r in rows:
            r["formatted"] = self.format_duration(r["seconds"])
            # Get top apps during this focus session
            r["top_apps"] = self.time_by_app(
                r["session_start"], r["session_end"], limit=5
            )
        return rows

    def parallel_activities(self, start: str, end: str) -> dict:
        """Show all data streams side-by-side to reveal parallel work.

        Combines window focus, VSCode edits, and browser tabs into a unified
        timeline showing what was happening simultaneously.
        """
        s, e = _date_to_ts(start), _date_to_ts(end)

        # Find VSCode edits that happened while a DIFFERENT app was focused
        background_coding = self._query("""
            WITH vscode_events AS (
                SELECT e.timestamp as vs_time,
                       json_extract(e.datastr, '$.file') as file,
                       json_extract(e.datastr, '$.language') as language
                FROM eventmodel e JOIN bucketmodel b ON e.bucket_id = b.key
                WHERE b.type = 'app.editor.activity'
                  AND e.timestamp >= ?
                  AND e.timestamp < ?
                  AND json_extract(e.datastr, '$.file') != 'unknown'
            )
            SELECT v.vs_time as timestamp,
                   v.file,
                   v.language,
                   json_extract(w.datastr, '$.app') as focused_app,
                   json_extract(w.datastr, '$.title') as focused_title,
                   ROUND(w.duration, 1) as focused_duration
            FROM vscode_events v
            JOIN eventmodel w ON v.vs_time >= w.timestamp
              AND v.vs_time < datetime(w.timestamp, '+' || MAX(CAST(w.duration AS INTEGER), 1) || ' seconds')
            JOIN bucketmodel wb ON w.bucket_id = wb.key
            WHERE wb.type = 'currentwindow'
              AND json_extract(w.datastr, '$.app') != 'Code'
            ORDER BY v.vs_time
        """, (s, e))

        # Multi-stream timeline — all sources interleaved
        timeline = self._query("""
            SELECT 'window' as source,
                   e.timestamp,
                   ROUND(e.duration, 1) as seconds,
                   json_extract(e.datastr, '$.app') as detail1,
                   json_extract(e.datastr, '$.title') as detail2
            FROM eventmodel e JOIN bucketmodel b ON e.bucket_id = b.key
            WHERE b.type = 'currentwindow'
              AND e.timestamp >= ? AND e.timestamp < ?
              AND e.duration > 2

            UNION ALL

            SELECT 'vscode' as source,
                   e.timestamp,
                   ROUND(e.duration, 1) as seconds,
                   json_extract(e.datastr, '$.language') as detail1,
                   json_extract(e.datastr, '$.file') as detail2
            FROM eventmodel e JOIN bucketmodel b ON e.bucket_id = b.key
            WHERE b.type = 'app.editor.activity'
              AND e.timestamp >= ? AND e.timestamp < ?
              AND json_extract(e.datastr, '$.file') != 'unknown'

            UNION ALL

            SELECT 'browser' as source,
                   e.timestamp,
                   ROUND(e.duration, 1) as seconds,
                   json_extract(e.datastr, '$.title') as detail1,
                   json_extract(e.datastr, '$.url') as detail2
            FROM eventmodel e JOIN bucketmodel b ON e.bucket_id = b.key
            WHERE b.type = 'web.tab.current'
              AND e.timestamp >= ? AND e.timestamp < ?
              AND e.duration > 2

            ORDER BY timestamp
            LIMIT 200
        """, (s, e, s, e, s, e))

        # Summarize background coding by focused app
        bg_summary: dict = {}
        for row in background_coding:
            app = row["focused_app"]
            bg_summary.setdefault(app, {"files": set(), "count": 0})
            bg_summary[app]["files"].add(row["file"])
            bg_summary[app]["count"] += 1
        bg_summary_list = [
            {"focused_app": app, "coding_events": d["count"],
             "files_edited": list(d["files"])}
            for app, d in sorted(bg_summary.items(), key=lambda x: -x[1]["count"])
        ]

        return {
            "background_coding": background_coding,
            "background_coding_summary": bg_summary_list,
            "multi_stream_timeline": timeline,
        }

    def editor_activity(self, start: str, end: str) -> list[dict]:
        """Get editor (VSCode) activity — files, languages, projects."""
        s, e = _date_to_ts(start), _date_to_ts(end)
        rows = self._query("""
            SELECT json_extract(e.datastr, '$.language') as language,
                   json_extract(e.datastr, '$.file') as file,
                   json_extract(e.datastr, '$.project') as project,
                   e.timestamp, e.duration
            FROM eventmodel e
            JOIN bucketmodel b ON e.bucket_id = b.key
            WHERE b.type = 'app.editor.activity'
              AND e.timestamp >= ?
              AND e.timestamp < ?
            ORDER BY e.timestamp DESC
            LIMIT 50
        """, (s, e))
        return rows

    def app_usage(
        self,
        days: int = 7,
        app: Optional[str] = None,
    ) -> dict:
        """Deep dive into app usage with daily breakdown."""
        end = date.today() + timedelta(days=1)
        start = end - timedelta(days=days)

        start_str = f"{start.isoformat()} 00:00:00"
        end_str = f"{end.isoformat()} 00:00:00"
        result: dict = {"days": days, "start": start.isoformat(), "end": end.isoformat()}

        if app:
            result["app"] = app
            result["total"] = self.time_by_app(start_str, end_str, limit=100)
            result["total"] = [r for r in result["total"] if r["app"] and r["app"].lower() == app.lower()]
            result["top_titles"] = self.time_by_title(start_str, end_str, app=app, limit=20)
            # Daily breakdown for this app
            daily = []
            for d in range(days):
                day = start + timedelta(days=d)
                day_start = f"{day.isoformat()} 00:00:00"
                day_end = f"{(day + timedelta(days=1)).isoformat()} 00:00:00"
                day_apps = self.time_by_app(day_start, day_end, limit=100)
                match = [r for r in day_apps if r["app"] and r["app"].lower() == app.lower()]
                daily.append({
                    "date": day.isoformat(),
                    "seconds": match[0]["seconds"] if match else 0,
                    "formatted": self.format_duration(match[0]["seconds"]) if match else "0m",
                })
            result["daily"] = daily
        else:
            result["top_apps"] = self.time_by_app(start_str, end_str, limit=20)
        return result

    def productivity_report(self, start: str, end: str) -> dict:
        """Generate productivity breakdown based on category config."""
        config = self.load_config()
        categories = config.get("categories", {
            "productive": ["Code", "iTerm2", "Terminal", "Notion", "Cursor"],
            "neutral": ["Slack", "Mail", "Calendar", "Microsoft Teams", "Zoom"],
            "distracting": ["Twitter", "Reddit", "YouTube", "Instagram", "TikTok"],
        })

        apps = self.time_by_app(start, end, limit=200)
        result: dict = {
            "productive": {"seconds": 0, "apps": []},
            "neutral": {"seconds": 0, "apps": []},
            "distracting": {"seconds": 0, "apps": []},
            "uncategorized": {"seconds": 0, "apps": []},
        }

        cat_map = {}
        for cat, app_list in categories.items():
            for a in app_list:
                cat_map[a.lower()] = cat

        for app_row in apps:
            app_name = app_row["app"] or "unknown"
            cat = cat_map.get(app_name.lower(), "uncategorized")
            if cat not in result:
                cat = "uncategorized"
            result[cat]["seconds"] += app_row["seconds"]
            result[cat]["apps"].append(app_row)

        total = sum(v["seconds"] for v in result.values())
        for cat in result:
            result[cat]["formatted"] = self.format_duration(result[cat]["seconds"])
            result[cat]["pct"] = round(result[cat]["seconds"] / total * 100, 1) if total else 0

        result["total_seconds"] = total
        result["total_formatted"] = self.format_duration(total)
        result["categories_config"] = categories
        return result

    # --- raw query support ---------------------------------------------------

    def run_aql_query(self, query: str, start: str, end: str) -> list:
        """Execute an AQL query via the REST API."""
        import requests

        timeperiods = [f"{start}/{end}"]
        resp = requests.post(
            f"{self.api_url}/query/",
            json={"timeperiods": timeperiods, "query": [query]},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def run_sql(self, sql: str) -> list[dict]:
        """Execute raw SQL against the ActivityWatch database (read-only)."""
        return self._query(sql)

    # --- project tracking ----------------------------------------------------

    def load_config(self) -> dict:
        """Load project/category config from disk."""
        if self._config_path.exists():
            return json.loads(self._config_path.read_text())
        return {"projects": {}, "categories": {}}

    def save_config(self, config: dict) -> None:
        """Save project/category config to disk."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(json.dumps(config, indent=2, default=str))

    def define_project(self, name: str, rules: dict) -> dict:
        """Define a project with matching rules."""
        config = self.load_config()
        config.setdefault("projects", {})[name] = {
            "rules": rules,
            "manual_entries": config.get("projects", {}).get(name, {}).get("manual_entries", []),
        }
        self.save_config(config)
        return {"status": "ok", "project": name, "rules": rules}

    def delete_project(self, name: str) -> dict:
        """Remove a project definition."""
        config = self.load_config()
        if name not in config.get("projects", {}):
            raise ValueError(f"Project not found: {name}")
        del config["projects"][name]
        self.save_config(config)
        return {"status": "ok", "deleted": name}

    def list_projects(self) -> list[dict]:
        """List all defined projects with summary stats."""
        config = self.load_config()
        projects = []
        for name, proj in config.get("projects", {}).items():
            projects.append({
                "name": name,
                "rules": proj.get("rules", {}),
                "manual_entries": len(proj.get("manual_entries", [])),
            })
        return projects

    def tag_time(
        self,
        start: str,
        end: str,
        project: str,
        notes: Optional[str] = None,
    ) -> dict:
        """Manually tag a time period to a project."""
        config = self.load_config()
        config.setdefault("projects", {}).setdefault(project, {"rules": {}, "manual_entries": []})
        entry = {"start": start, "end": end}
        if notes:
            entry["notes"] = notes
        config["projects"][project]["manual_entries"].append(entry)
        self.save_config(config)
        return {"status": "ok", "project": project, "entry": entry}

    def get_project_time(
        self,
        project: str,
        start: str,
        end: str,
    ) -> dict:
        """Calculate total time for a project (rule-matched + manual)."""
        config = self.load_config()
        proj = config.get("projects", {}).get(project)
        if not proj:
            raise ValueError(f"Project not found: {project}")

        rules = proj.get("rules", {})
        result: dict = {
            "project": project,
            "start": start,
            "end": end,
            "rule_matched": {"seconds": 0, "apps": []},
            "manual": {"seconds": 0, "entries": []},
        }

        # Rule-matched time via SQL
        if rules:
            all_apps = self.time_by_app(start, end, limit=200)
            app_patterns = [p.lower() for p in rules.get("app_patterns", [])]

            for app_row in all_apps:
                app_name = (app_row["app"] or "").lower()
                if any(pat in app_name for pat in app_patterns):
                    result["rule_matched"]["seconds"] += app_row["seconds"]
                    result["rule_matched"]["apps"].append(app_row)

            # Title-based matching
            title_patterns = [p.lower() for p in rules.get("title_patterns", [])]
            title_regex = rules.get("title_regex")
            if title_patterns or title_regex:
                titles = self.time_by_title(start, end, limit=500)
                for title_row in titles:
                    title = (title_row["title"] or "").lower()
                    matched = any(pat in title for pat in title_patterns)
                    if not matched and title_regex:
                        matched = bool(re.search(title_regex, title, re.IGNORECASE))
                    if matched:
                        # Avoid double-counting if app already matched
                        app_name = (title_row["app"] or "").lower()
                        if not any(pat in app_name for pat in app_patterns):
                            result["rule_matched"]["seconds"] += title_row["seconds"]
                            result["rule_matched"]["apps"].append(title_row)

        result["rule_matched"]["formatted"] = self.format_duration(result["rule_matched"]["seconds"])

        # Manual entries within the range
        for entry in proj.get("manual_entries", []):
            entry_start = entry["start"]
            entry_end = entry["end"]
            if entry_start < end and entry_end > start:
                # Calculate overlap
                overlap_start = max(entry_start, start)
                overlap_end = min(entry_end, end)
                try:
                    s = datetime.fromisoformat(overlap_start)
                    e = datetime.fromisoformat(overlap_end)
                    secs = (e - s).total_seconds()
                    if secs > 0:
                        result["manual"]["seconds"] += secs
                        result["manual"]["entries"].append({**entry, "overlap_seconds": secs})
                except ValueError:
                    pass
        result["manual"]["formatted"] = self.format_duration(result["manual"]["seconds"])

        result["total_seconds"] = result["rule_matched"]["seconds"] + result["manual"]["seconds"]
        result["total_formatted"] = self.format_duration(result["total_seconds"])
        return result

    # --- report generation ---------------------------------------------------

    def generate_daily_report(
        self,
        target_date: Optional[str] = None,
        fmt: str = "markdown",
    ) -> str | dict:
        """Generate a shareable daily activity report."""
        summary = self.daily_summary(target_date)
        if fmt == "json":
            return summary

        d = summary["date"]
        active = summary["active_time"]
        lines = [
            f"# Daily Activity Report — {d}",
            "",
            f"**Active time:** {active['active_formatted']} ({active['active_pct']}% of tracked time)",
            f"**AFK time:** {active['afk_formatted']}",
            "",
            "## Top Applications",
            "",
            "| App | Time |",
            "|-----|------|",
        ]
        for app in summary["top_apps"][:10]:
            lines.append(f"| {app['app']} | {app['formatted']} |")

        lines += ["", "## Top Window Titles", "", "| App | Title | Time |", "|-----|-------|------|"]
        for t in summary["top_titles"][:10]:
            title = (t["title"] or "")[:60]
            lines.append(f"| {t['app']} | {title} | {t['formatted']} |")

        if summary["editor_activity"]:
            lines += ["", "## Editor Activity (VSCode)", ""]
            langs = {}
            for ev in summary["editor_activity"]:
                lang = ev.get("language", "unknown")
                if lang and lang != "unknown":
                    langs[lang] = langs.get(lang, 0) + 1
            if langs:
                lines.append("**Languages:** " + ", ".join(
                    f"{l} ({c} events)" for l, c in sorted(langs.items(), key=lambda x: -x[1])
                ))
            files = list({ev.get("file", "") for ev in summary["editor_activity"] if ev.get("file") and ev["file"] != "unknown"})
            if files:
                lines += ["", "**Files touched:**"]
                for f in files[:15]:
                    lines.append(f"- `{f}`")

        return "\n".join(lines)

    def generate_weekly_report(
        self,
        week_start: Optional[str] = None,
        fmt: str = "markdown",
    ) -> str | dict:
        """Generate a weekly summary report."""
        if not week_start:
            today = date.today()
            start_date = today - timedelta(days=today.weekday())  # Monday
        else:
            start_date = date.fromisoformat(week_start)
        end_date = start_date + timedelta(days=7)
        start = f"{start_date.isoformat()} 00:00:00"
        end = f"{end_date.isoformat()} 00:00:00"

        daily = self.range_summary(start, end, group_by="day")
        apps = self.time_by_app(start, end, limit=15)
        active = self.active_time(start, end)

        data = {
            "week_start": start_date.isoformat(),
            "week_end": end_date.isoformat(),
            "active_time": active,
            "daily_breakdown": daily,
            "top_apps": apps,
        }

        if fmt == "json":
            return data

        lines = [
            f"# Weekly Activity Report — {start_date} to {end_date}",
            "",
            f"**Total active time:** {active['active_formatted']}",
            "",
            "## Daily Breakdown",
            "",
            "| Day | Active Time |",
            "|-----|-------------|",
        ]
        for d in daily:
            lines.append(f"| {d.get('day', '?')} | {d['formatted']} |")

        lines += [
            "",
            "## Top Applications",
            "",
            "| App | Time |",
            "|-----|------|",
        ]
        for app in apps[:10]:
            lines.append(f"| {app['app']} | {app['formatted']} |")

        return "\n".join(lines)

    def generate_project_report(
        self,
        project: str,
        start: str,
        end: str,
        fmt: str = "markdown",
    ) -> str | dict:
        """Generate a project-specific time report."""
        proj_time = self.get_project_time(project, start, end)
        if fmt == "json":
            return proj_time

        lines = [
            f"# Project Report — {project}",
            f"**Period:** {start[:10]} to {end[:10]}",
            "",
            f"**Total time:** {proj_time['total_formatted']}",
            f"- Rule-matched: {proj_time['rule_matched']['formatted']}",
            f"- Manual entries: {proj_time['manual']['formatted']}",
            "",
        ]

        if proj_time["rule_matched"]["apps"]:
            lines += [
                "## Matched Applications",
                "",
                "| App | Time |",
                "|-----|------|",
            ]
            for app in proj_time["rule_matched"]["apps"]:
                lines.append(f"| {app.get('app', '')} | {app['formatted']} |")

        if proj_time["manual"]["entries"]:
            lines += [
                "",
                "## Manual Entries",
                "",
                "| Start | End | Notes |",
                "|-------|-----|-------|",
            ]
            for e in proj_time["manual"]["entries"]:
                notes = e.get("notes", "")
                lines.append(f"| {e['start']} | {e['end']} | {notes} |")

        return "\n".join(lines)

    def generate_activity_story(
        self,
        target_date: Optional[str] = None,
        fmt: str = "markdown",
    ) -> str | dict:
        """Generate a rich, presentable activity report with timeline and parallel work.

        Includes: hourly timeline with visual bars, work blocks, parallel
        activity highlights, focus sessions, and app breakdown.
        """
        if not target_date:
            target_date = date.today().isoformat()
        start = f"{target_date} 00:00:00"
        end_date = date.fromisoformat(target_date) + timedelta(days=1)
        end = f"{end_date.isoformat()} 00:00:00"

        # Gather all data
        active = self.active_time(start, end)
        top_apps = self.time_by_app(start, end, limit=20)
        top_titles = self.time_by_title(start, end, limit=20)
        editor = self.editor_activity(start, end)
        parallel = self.parallel_activities(start, end)
        focus = self.find_focus_sessions(start, end, min_minutes=20)

        # Hourly breakdown (all apps per hour, AFK-filtered)
        hourly_raw = self._query(f"""
            WITH {self._afk_cte(start, end)}
            SELECT strftime('%H', w.timestamp, 'localtime') as hour,
                   json_extract(w.datastr, '$.app') as app,
                   ROUND(SUM(
                       (MIN(julianday(a.afk_end),
                            julianday(datetime(w.timestamp, '+' || CAST(w.duration AS INTEGER) || ' seconds')))
                        - MAX(julianday(w.timestamp), julianday(a.afk_start))
                       ) * 86400
                   ), 0) as seconds
            FROM eventmodel w
            JOIN bucketmodel wb ON w.bucket_id = wb.key
            JOIN afk_periods a ON w.timestamp < a.afk_end
                AND datetime(w.timestamp, '+' || CAST(w.duration AS INTEGER) || ' seconds') > a.afk_start
            WHERE wb.type = 'currentwindow'
              AND w.duration > 0
              AND w.timestamp >= ?
              AND w.timestamp < ?
            GROUP BY hour, app
            HAVING seconds > 10
            ORDER BY hour, seconds DESC
        """, (_date_to_ts(start), _date_to_ts(end)))

        # Build hourly structure
        hourly: dict = {}
        for row in hourly_raw:
            h = int(row["hour"])
            hourly.setdefault(h, []).append(row)

        # Work blocks — contiguous hours of activity
        work_blocks = []
        active_hours = sorted(hourly.keys())
        if active_hours:
            block_start = active_hours[0]
            prev = active_hours[0]
            for h in active_hours[1:]:
                if h - prev > 1:
                    work_blocks.append((block_start, prev))
                    block_start = h
                prev = h
            work_blocks.append((block_start, prev))

        if fmt == "json":
            return {
                "date": target_date,
                "active_time": active,
                "top_apps": top_apps,
                "top_titles": top_titles,
                "editor_activity": editor,
                "parallel_activities": parallel,
                "focus_sessions": focus,
                "hourly": hourly_raw,
                "work_blocks": [{"start": s, "end": e} for s, e in work_blocks],
            }

        # --- Build markdown ---
        BAR_MAX = 20
        day_label = datetime.strptime(target_date, "%Y-%m-%d").strftime("%A, %B %-d, %Y")

        lines = [
            f"# Activity Story — {day_label}",
            "",
        ]

        # Overview box
        total_active = active["active_seconds"]
        block_strs = []
        for bs, be in work_blocks:
            if bs == be:
                block_strs.append(f"{bs:02d}:00")
            else:
                block_strs.append(f"{bs:02d}:00–{be:02d}:59")

        lines += [
            f"> **{active['active_formatted']}** active "
            f"({active['active_pct']}% of tracked time)  ",
            f"> Work blocks: {', '.join(block_strs) if block_strs else 'none detected'}  ",
            f"> Focus sessions: {len(focus)} "
            f"({'longest: ' + focus[0]['formatted'] if focus else 'none'} )",
            "",
        ]

        # --- Hourly Timeline ---
        lines += ["## Hourly Timeline", ""]

        # Find the max hour total for scaling bars
        hour_totals = {}
        for h, apps in hourly.items():
            hour_totals[h] = sum(a["seconds"] for a in apps)
        max_hour = max(hour_totals.values()) if hour_totals else 1

        lines.append("```")
        for h in range(24):
            if h not in hourly:
                lines.append(f"  {h:02d}:00  {'·' * BAR_MAX}")
                continue
            total = hour_totals[h]
            bar_len = max(1, int(total / max_hour * BAR_MAX))
            top_app = hourly[h][0]["app"] if hourly[h] else ""
            bar = "█" * bar_len + "░" * (BAR_MAX - bar_len)
            lines.append(f"  {h:02d}:00  {bar}  {self.format_duration(total)}  {top_app}")
        lines.append("```")
        lines.append("")

        # --- Top Apps ---
        lines += ["## Top Applications", ""]
        if top_apps:
            max_app_time = top_apps[0]["seconds"] if top_apps else 1
            for app in top_apps[:10]:
                bar_len = max(1, int(app["seconds"] / max_app_time * 16))
                pct = round(app["seconds"] / total_active * 100, 1) if total_active else 0
                bar = "▓" * bar_len
                lines.append(f"  {bar} **{app['app']}** — {app['formatted']} ({pct}%)")
            lines.append("")

        # --- Focus Sessions ---
        if focus:
            lines += ["## Focus Sessions", ""]
            for i, sess in enumerate(focus, 1):
                sess_start = sess["session_start"]
                try:
                    t = _utc_to_local(sess_start)
                    time_str = t.strftime("%-I:%M %p")
                except Exception:
                    time_str = sess_start[:16]
                app_list = ", ".join(
                    f"{a['app']} ({a['formatted']})" for a in sess.get("top_apps", [])[:3]
                )
                lines.append(f"{i}. **{sess['formatted']}** starting {time_str}")
                if app_list:
                    lines.append(f"   Apps: {app_list}")
            lines.append("")

        # --- Parallel Activities ---
        bg = parallel.get("background_coding", [])
        bg_summary = parallel.get("background_coding_summary", [])
        if bg:
            lines += ["## Parallel Work", ""]
            lines.append(
                f"Detected **{len(bg)} background coding events** "
                "(VSCode edits while a different app was focused):"
            )
            lines.append("")
            for item in bg_summary:
                files = item.get("files_edited", [])
                file_list = ", ".join(f"`{f.split('/')[-1]}`" for f in files[:5])
                lines.append(
                    f"- While in **{item['focused_app']}**: "
                    f"edited {file_list} ({item['coding_events']} edits)"
                )
            lines.append("")

        # --- What I worked on (top titles, deduplicated) ---
        lines += ["## Key Activities", ""]
        lines.append("| Application | What | Time |")
        lines.append("|-------------|------|------|")
        seen = set()
        for t in top_titles[:15]:
            title_raw = t.get("title") or ""
            app = t.get("app") or ""
            # Clean up titles — strip browser suffixes, hostname markers
            title = title_raw
            for suffix in [" - Google Chrome", " - Trent (40hero.com)",
                           " - Audio playing", " - Camera and microphone recording"]:
                title = title.replace(suffix, "")
            title = title.strip(" -–—")
            if len(title) > 55:
                title = title[:52] + "..."
            key = (app, title[:30])
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"| {app} | {title} | {t['formatted']} |")
        lines.append("")

        # --- Editor Activity ---
        if editor:
            lines += ["## Editor Activity", ""]
            langs: dict = {}
            files_set: set = set()
            projects_set: set = set()
            for ev in editor:
                lang = ev.get("language", "")
                if lang and lang != "unknown":
                    langs[lang] = langs.get(lang, 0) + 1
                f = ev.get("file", "")
                if f and f != "unknown":
                    files_set.add(f)
                p = ev.get("project", "")
                if p and p != "unknown":
                    projects_set.add(p)

            if projects_set:
                lines.append("**Projects:** " + ", ".join(sorted(projects_set)))
            if langs:
                lang_str = ", ".join(
                    f"{l} ({c})" for l, c in sorted(langs.items(), key=lambda x: -x[1])
                )
                lines.append(f"**Languages:** {lang_str}")
            if files_set:
                lines += ["", "**Files touched:**"]
                for f in sorted(files_set)[:15]:
                    short = "/".join(f.split("/")[-3:]) if len(f) > 60 else f
                    lines.append(f"- `{short}`")
            lines.append("")

        lines.append("---")
        lines.append(f"*Generated from ActivityWatch data on {date.today().isoformat()}*")

        return "\n".join(lines)

    # --- visual HTML report ---------------------------------------------------

    _APP_COLORS = {
        "Google Chrome": "#4285F4",
        "Code": "#007ACC",
        "Claude": "#D97757",
        "Cursor": "#7C3AED",
        "Notion": "#000000",
        "Slack": "#4A154B",
        "Discord": "#5865F2",
        "Terminal": "#2D2D2D",
        "iTerm2": "#2D2D2D",
        "Termius": "#2D2D2D",
        "Messages": "#34C759",
        "\u200eWhatsApp": "#25D366",
        "WhatsApp": "#25D366",
        "Finder": "#3B82F6",
        "Microsoft Word": "#2B579A",
        "Microsoft Excel": "#217346",
        "Microsoft Teams": "#6264A7",
        "Zoom": "#2D8CFF",
        "Safari": "#006CFF",
        "Mail": "#007AFF",
        "Notion Calendar": "#EA4335",
        "loginwindow": "#8B8B8B",
        "Sublime Text": "#FF9800",
        "Shortcuts": "#EF4444",
    }
    _PALETTE = [
        "#4285F4", "#EA4335", "#FBBC05", "#34A853", "#FF6D01",
        "#46BDC6", "#7C3AED", "#EC4899", "#F97316", "#06B6D4",
        "#8B5CF6", "#10B981", "#F59E0B", "#EF4444", "#3B82F6",
    ]

    def _app_color(self, app: str, idx: int = 0) -> str:
        """Get a consistent color for an app name."""
        return self._APP_COLORS.get(app, self._PALETTE[idx % len(self._PALETTE)])

    def generate_html_report(
        self,
        target_date: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """Generate a visual HTML report with charts, timelines, and parallel tracks.

        Returns the file path of the generated HTML report.
        """
        import html as html_mod

        if not target_date:
            target_date = date.today().isoformat()
        start = f"{target_date} 00:00:00"
        end_date = date.fromisoformat(target_date) + timedelta(days=1)
        end = f"{end_date.isoformat()} 00:00:00"

        # Gather data
        active = self.active_time(start, end)
        top_apps = self.time_by_app(start, end, limit=20)
        top_titles = self.time_by_title(start, end, limit=20)
        editor = self.editor_activity(start, end)
        parallel = self.parallel_activities(start, end)
        focus = self.find_focus_sessions(start, end, min_minutes=20)

        # Hourly breakdown (AFK-filtered)
        hourly_raw = self._query(f"""
            WITH {self._afk_cte(start, end)}
            SELECT strftime('%H', w.timestamp, 'localtime') as hour,
                   json_extract(w.datastr, '$.app') as app,
                   ROUND(SUM(
                       (MIN(julianday(a.afk_end),
                            julianday(datetime(w.timestamp, '+' || CAST(w.duration AS INTEGER) || ' seconds')))
                        - MAX(julianday(w.timestamp), julianday(a.afk_start))
                       ) * 86400
                   ), 0) as seconds
            FROM eventmodel w
            JOIN bucketmodel wb ON w.bucket_id = wb.key
            JOIN afk_periods a ON w.timestamp < a.afk_end
                AND datetime(w.timestamp, '+' || CAST(w.duration AS INTEGER) || ' seconds') > a.afk_start
            WHERE wb.type = 'currentwindow'
              AND w.duration > 0
              AND w.timestamp >= ?
              AND w.timestamp < ?
            GROUP BY hour, app
            HAVING seconds > 10
            ORDER BY hour, seconds DESC
        """, (_date_to_ts(start), _date_to_ts(end)))

        hourly: dict = {}
        for row in hourly_raw:
            h = int(row["hour"])
            hourly.setdefault(h, []).append(row)

        # Assign colors to all apps
        all_apps_seen = list(dict.fromkeys(
            a["app"] for a in top_apps if a["app"]
        ))
        app_colors = {
            app: self._app_color(app, i) for i, app in enumerate(all_apps_seen)
        }

        # Work blocks
        active_hours = sorted(hourly.keys())
        work_blocks = []
        if active_hours:
            bs = active_hours[0]
            prev = active_hours[0]
            for h in active_hours[1:]:
                if h - prev > 1:
                    work_blocks.append((bs, prev))
                    bs = h
                prev = h
            work_blocks.append((bs, prev))

        day_label = datetime.strptime(target_date, "%Y-%m-%d").strftime("%A, %B %-d, %Y")
        total_active = active["active_seconds"]

        # --- Parallel tracks data (window + vscode + browser sampled by minute) ---
        def _parallel_track_data():
            """Build minute-by-minute parallel track arrays for the swim lane viz."""
            timeline = parallel.get("multi_stream_timeline", [])
            tracks: dict = {"window": {}, "vscode": {}, "browser": {}}
            for ev in timeline:
                src = ev.get("source", "")
                if src not in tracks:
                    continue
                try:
                    ts = _utc_to_local(ev["timestamp"])
                    minute = ts.hour * 60 + ts.minute
                    dur = float(ev.get("seconds", 0))
                    app = ev.get("detail1", "") or ""
                    end_min = minute + max(1, int(dur / 60))
                    for m in range(minute, min(end_min, 1440)):
                        if m not in tracks[src] or dur > 10:
                            tracks[src][m] = app
                except Exception:
                    continue
            return tracks

        tracks = _parallel_track_data()

        # Find active time range for parallel viz
        all_minutes = set()
        for t in tracks.values():
            all_minutes.update(t.keys())
        if all_minutes:
            viz_start = max(0, (min(all_minutes) // 60) * 60)
            viz_end = min(1440, ((max(all_minutes) // 60) + 1) * 60 + 60)
        else:
            viz_start, viz_end = 0, 1440

        # --- Build HTML ---
        def esc(s):
            return html_mod.escape(str(s)) if s else ""

        # Chart.js data for donut
        chart_labels = json.dumps([a["app"] for a in top_apps[:10]])
        chart_data = json.dumps([round(a["seconds"]) for a in top_apps[:10]])
        chart_colors = json.dumps([app_colors.get(a["app"], "#888") for a in top_apps[:10]])

        # Hourly timeline HTML
        hour_totals = {h: sum(a["seconds"] for a in apps) for h, apps in hourly.items()}
        max_hour = max(hour_totals.values()) if hour_totals else 1

        timeline_rows = []
        for h in range(24):
            label = f"{h:02d}:00"
            if h not in hourly:
                timeline_rows.append(f"""
                    <div class="hour-row">
                        <span class="hour-label">{label}</span>
                        <div class="hour-bar empty"></div>
                        <span class="hour-time"></span>
                    </div>""")
                continue
            total = hour_totals[h]
            pct = total / max_hour * 100
            segments = []
            for a in hourly[h]:
                seg_pct = a["seconds"] / total * 100
                color = app_colors.get(a["app"], "#888")
                segments.append(
                    f'<div class="seg" style="width:{seg_pct:.1f}%;background:{color}" '
                    f'title="{esc(a["app"])}: {self.format_duration(a["seconds"])}"></div>'
                )
            timeline_rows.append(f"""
                <div class="hour-row">
                    <span class="hour-label">{label}</span>
                    <div class="hour-bar" style="width:{pct:.1f}%">{''.join(segments)}</div>
                    <span class="hour-time">{self.format_duration(total)}</span>
                </div>""")

        # Focus sessions HTML
        focus_html = ""
        if focus:
            items = []
            for sess in focus:
                try:
                    t = _utc_to_local(sess["session_start"])
                    time_str = t.strftime("%-I:%M %p")
                except Exception:
                    time_str = sess["session_start"][:16]
                apps_str = ", ".join(
                    f"{a['app']} ({a['formatted']})" for a in sess.get("top_apps", [])[:3]
                )
                items.append(f"""
                    <div class="focus-item">
                        <div class="focus-dur">{esc(sess['formatted'])}</div>
                        <div class="focus-detail">Starting {esc(time_str)}<br>
                        <span class="focus-apps">{esc(apps_str)}</span></div>
                    </div>""")
            focus_html = "\n".join(items)

        # Parallel tracks SVG
        track_names = ["Window Focus", "Editor (VSCode)", "Browser"]
        track_keys = ["window", "vscode", "browser"]
        track_height = 28
        track_gap = 4
        svg_height = len(track_names) * (track_height + track_gap) + 40
        total_minutes = viz_end - viz_start
        svg_width = 800

        svg_parts = [
            f'<svg viewBox="0 0 {svg_width} {svg_height}" class="parallel-svg">'
        ]
        # Hour markers
        for m in range(viz_start, viz_end, 60):
            x = (m - viz_start) / total_minutes * svg_width if total_minutes else 0
            h = m // 60
            svg_parts.append(
                f'<line x1="{x}" y1="0" x2="{x}" y2="{svg_height}" '
                f'stroke="#333" stroke-width="0.5" stroke-dasharray="2,4"/>'
                f'<text x="{x+3}" y="12" fill="#888" font-size="10">{h:02d}:00</text>'
            )
        # Tracks
        for ti, (tname, tkey) in enumerate(zip(track_names, track_keys)):
            y = 20 + ti * (track_height + track_gap)
            # Background
            svg_parts.append(
                f'<rect x="0" y="{y}" width="{svg_width}" height="{track_height}" '
                f'fill="#1a1a2e" rx="3"/>'
            )
            # Events as colored blocks
            track_data = tracks.get(tkey, {})
            if track_data:
                # Group consecutive minutes with same app into blocks
                sorted_mins = sorted(track_data.keys())
                blocks: list = []
                if sorted_mins:
                    cur_app = track_data[sorted_mins[0]]
                    cur_start = sorted_mins[0]
                    cur_end = sorted_mins[0]
                    for m in sorted_mins[1:]:
                        if m == cur_end + 1 and track_data[m] == cur_app:
                            cur_end = m
                        else:
                            blocks.append((cur_start, cur_end, cur_app))
                            cur_app = track_data[m]
                            cur_start = m
                            cur_end = m
                    blocks.append((cur_start, cur_end, cur_app))

                for bstart, bend, bapp in blocks:
                    if bstart < viz_start or bstart >= viz_end:
                        continue
                    x1 = (bstart - viz_start) / total_minutes * svg_width
                    x2 = (bend + 1 - viz_start) / total_minutes * svg_width
                    w = max(2, x2 - x1)
                    color = app_colors.get(bapp, "#666")
                    svg_parts.append(
                        f'<rect x="{x1:.1f}" y="{y+1}" width="{w:.1f}" '
                        f'height="{track_height-2}" fill="{color}" rx="2" '
                        f'opacity="0.85"><title>{esc(bapp)}</title></rect>'
                    )
            # Track label
            svg_parts.append(
                f'<text x="4" y="{y + track_height - 8}" fill="#ccc" '
                f'font-size="10" font-weight="bold" opacity="0.7">{esc(tname)}</text>'
            )
        svg_parts.append('</svg>')
        parallel_svg = "\n".join(svg_parts)

        # App legend
        legend_items = []
        for app in all_apps_seen[:12]:
            color = app_colors.get(app, "#888")
            legend_items.append(
                f'<span class="legend-item">'
                f'<span class="legend-dot" style="background:{color}"></span>'
                f'{esc(app)}</span>'
            )
        legend_html = " ".join(legend_items)

        # Key activities table
        activity_rows = []
        seen: set = set()
        for t in top_titles[:12]:
            title_raw = t.get("title") or ""
            app = t.get("app") or ""
            title = title_raw
            for suffix in [" - Google Chrome", " - Trent (40hero.com)",
                           " - Audio playing", " - Camera and microphone recording",
                           " - Trent"]:
                title = title.replace(suffix, "")
            title = title.strip(" -–—")
            if len(title) > 60:
                title = title[:57] + "..."
            key = (app, title[:30])
            if key in seen:
                continue
            seen.add(key)
            color = app_colors.get(app, "#888")
            activity_rows.append(
                f'<tr><td><span class="app-badge" style="background:{color}">'
                f'{esc(app)}</span></td><td>{esc(title)}</td>'
                f'<td class="time-col">{esc(t["formatted"])}</td></tr>'
            )

        # Background coding
        bg_html = ""
        bg_summary = parallel.get("background_coding_summary", [])
        if bg_summary:
            bg_items = []
            for item in bg_summary:
                files = item.get("files_edited", [])
                file_names = ", ".join(f.split("/")[-1] for f in files[:4])
                bg_items.append(
                    f'<div class="bg-item">'
                    f'<strong>{esc(item["focused_app"])}</strong> was focused '
                    f'&rarr; edited <code>{esc(file_names)}</code> '
                    f'({item["coding_events"]} edits)</div>'
                )
            bg_html = "\n".join(bg_items)

        # Editor summary
        editor_html = ""
        if editor:
            langs: dict = {}
            files_set: set = set()
            projects_set: set = set()
            for ev in editor:
                lang = ev.get("language", "")
                if lang and lang != "unknown":
                    langs[lang] = langs.get(lang, 0) + 1
                f = ev.get("file", "")
                if f and f != "unknown":
                    files_set.add(f)
                p = ev.get("project", "")
                if p and p != "unknown":
                    projects_set.add(p)
            parts = []
            if projects_set:
                proj_names = [p.split("/")[-1] for p in sorted(projects_set)]
                parts.append(f'<div class="editor-stat"><strong>Projects:</strong> {esc(", ".join(proj_names))}</div>')
            if langs:
                lang_str = ", ".join(f"{l} ({c})" for l, c in sorted(langs.items(), key=lambda x: -x[1]))
                parts.append(f'<div class="editor-stat"><strong>Languages:</strong> {esc(lang_str)}</div>')
            if files_set:
                file_list = "".join(
                    f'<li><code>{esc("/".join(f.split("/")[-3:]))}</code></li>'
                    for f in sorted(files_set)[:12]
                )
                parts.append(f'<div class="editor-stat"><strong>Files:</strong><ul>{file_list}</ul></div>')
            editor_html = "\n".join(parts)

        # Work blocks summary
        block_strs = []
        for bs, be in work_blocks:
            if bs == be:
                block_strs.append(f"{bs:02d}:00")
            else:
                block_strs.append(f"{bs:02d}:00 – {be:02d}:59")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Activity Report — {esc(day_label)}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0f0f1a; --card: #16162a; --border: #2a2a45;
    --text: #e0e0f0; --muted: #8888aa; --accent: #D97757;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg); color: var(--text);
    max-width: 960px; margin: 0 auto; padding: 24px 20px;
    line-height: 1.5;
  }}
  h1 {{ font-size: 1.8rem; margin-bottom: 4px; }}
  h1 span {{ color: var(--accent); }}
  .subtitle {{ color: var(--muted); margin-bottom: 24px; font-size: 0.95rem; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 28px; }}
  .card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px;
  }}
  .card-value {{ font-size: 1.6rem; font-weight: 700; color: var(--accent); }}
  .card-label {{ font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }}
  .section {{ margin-bottom: 32px; }}
  .section-title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid var(--border); }}

  /* Timeline */
  .hour-row {{ display: flex; align-items: center; height: 22px; margin-bottom: 2px; }}
  .hour-label {{ width: 48px; font-size: 0.75rem; color: var(--muted); text-align: right; padding-right: 8px; flex-shrink: 0; }}
  .hour-bar {{
    height: 18px; border-radius: 3px; display: flex; overflow: hidden;
    transition: width 0.3s;
  }}
  .hour-bar.empty {{ width: 100%; background: #1a1a2e; height: 4px; margin-top: 7px; border-radius: 2px; }}
  .seg {{ height: 100%; min-width: 2px; }}
  .seg:first-child {{ border-radius: 3px 0 0 3px; }}
  .seg:last-child {{ border-radius: 0 3px 3px 0; }}
  .hour-time {{ font-size: 0.72rem; color: var(--muted); margin-left: 8px; flex-shrink: 0; min-width: 36px; }}

  /* Charts */
  .chart-row {{ display: grid; grid-template-columns: 260px 1fr; gap: 24px; align-items: start; }}
  .chart-container {{ position: relative; width: 240px; height: 240px; }}
  .app-list {{ list-style: none; }}
  .app-list li {{ display: flex; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 0.9rem; }}
  .app-list li:last-child {{ border: none; }}
  .app-bar-wrap {{ flex: 1; margin: 0 10px; height: 8px; background: #1a1a2e; border-radius: 4px; overflow: hidden; }}
  .app-bar {{ height: 100%; border-radius: 4px; }}
  .app-pct {{ color: var(--muted); font-size: 0.8rem; min-width: 40px; text-align: right; }}

  /* Legend */
  .legend {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }}
  .legend-item {{ display: flex; align-items: center; gap: 4px; font-size: 0.8rem; color: var(--muted); }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}

  /* Parallel tracks */
  .parallel-svg {{ width: 100%; height: auto; }}

  /* Focus sessions */
  .focus-item {{ display: flex; align-items: flex-start; gap: 12px; margin-bottom: 10px; padding: 10px; background: var(--card); border: 1px solid var(--border); border-radius: 8px; }}
  .focus-dur {{ font-size: 1.1rem; font-weight: 700; color: var(--accent); min-width: 60px; }}
  .focus-detail {{ font-size: 0.9rem; }}
  .focus-apps {{ color: var(--muted); font-size: 0.82rem; }}

  /* Table */
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; font-size: 0.75rem; color: var(--muted); text-transform: uppercase; padding: 6px 8px; border-bottom: 1px solid var(--border); }}
  td {{ padding: 8px; border-bottom: 1px solid var(--border); font-size: 0.9rem; }}
  .time-col {{ text-align: right; color: var(--muted); white-space: nowrap; }}
  .app-badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; color: #fff; font-size: 0.78rem; font-weight: 600; white-space: nowrap; }}

  /* Background coding */
  .bg-item {{ padding: 8px 12px; margin-bottom: 6px; background: var(--card); border: 1px solid var(--border); border-radius: 6px; font-size: 0.88rem; }}
  .bg-item code {{ background: #222240; padding: 1px 5px; border-radius: 3px; font-size: 0.82rem; }}

  /* Editor */
  .editor-stat {{ margin-bottom: 6px; font-size: 0.9rem; }}
  .editor-stat ul {{ margin-top: 4px; padding-left: 18px; }}
  .editor-stat li {{ font-size: 0.82rem; margin-bottom: 2px; }}
  .editor-stat code {{ background: #222240; padding: 1px 5px; border-radius: 3px; font-size: 0.8rem; }}

  .footer {{ text-align: center; color: var(--muted); font-size: 0.78rem; margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--border); }}

  @media (max-width: 700px) {{
    .chart-row {{ grid-template-columns: 1fr; }}
    .chart-container {{ margin: 0 auto; }}
  }}
</style>
</head>
<body>

<h1>Activity Report — <span>{esc(day_label)}</span></h1>
<div class="subtitle">Generated from ActivityWatch data</div>

<div class="cards">
  <div class="card">
    <div class="card-value">{esc(active['active_formatted'])}</div>
    <div class="card-label">Active Time</div>
  </div>
  <div class="card">
    <div class="card-value">{active['active_pct']}%</div>
    <div class="card-label">Active Rate</div>
  </div>
  <div class="card">
    <div class="card-value">{len(focus)}</div>
    <div class="card-label">Focus Sessions</div>
  </div>
  <div class="card">
    <div class="card-value">{esc(', '.join(block_strs) if block_strs else 'none')}</div>
    <div class="card-label">Work Blocks</div>
  </div>
</div>

<div class="section">
  <div class="section-title">Hourly Timeline</div>
  <div class="legend">{legend_html}</div>
  {''.join(timeline_rows)}
</div>

<div class="section">
  <div class="section-title">App Breakdown</div>
  <div class="chart-row">
    <div class="chart-container"><canvas id="appChart"></canvas></div>
    <ul class="app-list">
      {''.join(
          f'<li>'
          f'<span style="color:{app_colors.get(a["app"], "#888")};min-width:100px;font-weight:600">{esc(a["app"])}</span>'
          f'<div class="app-bar-wrap"><div class="app-bar" style="width:{a["seconds"]/top_apps[0]["seconds"]*100:.1f}%;background:{app_colors.get(a["app"], "#888")}"></div></div>'
          f'<span class="app-pct">{esc(a["formatted"])}</span>'
          f'</li>'
          for a in top_apps[:10]
      )}
    </ul>
  </div>
</div>

<div class="section">
  <div class="section-title">Parallel Activity Streams</div>
  <p style="color:var(--muted);font-size:0.82rem;margin-bottom:8px">
    Three tracks showing simultaneous data streams — hover for app names
  </p>
  {parallel_svg}
</div>

{'<div class="section"><div class="section-title">Focus Sessions</div>' + focus_html + '</div>' if focus_html else ''}

{'<div class="section"><div class="section-title">Background Coding</div><p style="color:var(--muted);font-size:0.85rem;margin-bottom:8px">VSCode edits detected while a different app was focused</p>' + bg_html + '</div>' if bg_html else ''}

<div class="section">
  <div class="section-title">Key Activities</div>
  <table>
    <tr><th>App</th><th>Activity</th><th style="text-align:right">Time</th></tr>
    {''.join(activity_rows)}
  </table>
</div>

{'<div class="section"><div class="section-title">Editor Activity</div>' + editor_html + '</div>' if editor_html else ''}

<div class="footer">
  Generated from ActivityWatch &middot; {target_date}
</div>

<script>
new Chart(document.getElementById('appChart'), {{
  type: 'doughnut',
  data: {{
    labels: {chart_labels},
    datasets: [{{
      data: {chart_data},
      backgroundColor: {chart_colors},
      borderWidth: 0,
      hoverOffset: 6,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: true,
    cutout: '62%',
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          label: function(ctx) {{
            var secs = ctx.raw;
            var h = Math.floor(secs/3600);
            var m = Math.floor((secs%3600)/60);
            return ctx.label + ': ' + (h ? h+'h ':'') + m + 'm';
          }}
        }}
      }}
    }}
  }}
}});
</script>
</body>
</html>"""

        # Write to file
        if not output_path:
            output_dir = Path.home() / "Desktop"
            output_path = str(output_dir / f"activity-report-{target_date}.html")

        Path(output_path).write_text(html)
        return output_path

    # --- export --------------------------------------------------------------

    def export_range(
        self,
        start: str,
        end: str,
        bucket_ids: Optional[list[str]] = None,
        fmt: str = "json",
    ) -> list[dict] | str:
        """Export events for a date range."""
        s, e = _date_to_ts(start), _date_to_ts(end)
        if bucket_ids:
            placeholders = ",".join("?" for _ in bucket_ids)
            sql = f"""
                SELECT b.id as bucket_id, e.timestamp, e.duration, e.datastr
                FROM eventmodel e
                JOIN bucketmodel b ON e.bucket_id = b.key
                WHERE b.id IN ({placeholders})
                  AND e.timestamp >= ?
                  AND e.timestamp < ?
                ORDER BY e.timestamp
            """
            params = tuple(bucket_ids) + (s, e)
        else:
            sql = """
                SELECT b.id as bucket_id, e.timestamp, e.duration, e.datastr
                FROM eventmodel e
                JOIN bucketmodel b ON e.bucket_id = b.key
                WHERE e.timestamp >= ?
                  AND e.timestamp < ?
                ORDER BY e.timestamp
            """
            params = (s, e)

        events = self._query(sql, params)
        for ev in events:
            ev["data"] = json.loads(ev.pop("datastr"))

        if fmt == "csv":
            if not events:
                return "bucket_id,timestamp,duration,data\n"
            lines = ["bucket_id,timestamp,duration,data"]
            for ev in events:
                data_str = json.dumps(ev["data"]).replace('"', '""')
                lines.append(f'{ev["bucket_id"]},{ev["timestamp"]},{ev["duration"]},"{data_str}"')
            return "\n".join(lines)
        return events

    def export_all(self) -> dict:
        """Export all buckets and events."""
        buckets = self.list_buckets()
        result = {}
        for b in buckets:
            events = self.get_events(b["id"], limit=999999)
            result[b["id"]] = {
                "bucket": b,
                "events": events,
            }
        return result

    # --- formatting helpers --------------------------------------------------

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format seconds as human-readable duration."""
        if not seconds or seconds < 0:
            return "0m"
        seconds = float(seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        if minutes > 0:
            return f"{minutes}m"
        return f"{int(seconds)}s"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_date_arg(value: str) -> str:
    """Parse flexible date input into ISO format."""
    if value == "today":
        return date.today().isoformat()
    if value == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    return value


def main():
    parser = argparse.ArgumentParser(description="ActivityWatch time analysis")
    parser.add_argument("--output-format", "-f", default="text",
                        choices=["text", "json", "markdown"],
                        help="Output format")
    sub = parser.add_subparsers(dest="command", help="Command")

    # -- buckets --
    bp = sub.add_parser("buckets", help="Bucket operations")
    bsub = bp.add_subparsers(dest="action")
    bsub.add_parser("list", help="List all buckets")
    bi = bsub.add_parser("info", help="Get bucket info")
    bi.add_argument("bucket_id", help="Bucket ID")

    # -- events --
    ep = sub.add_parser("events", help="Event operations")
    ep.add_argument("bucket_id", help="Bucket ID")
    ep.add_argument("--limit", type=int, default=20)
    ep.add_argument("--start", help="Start date (ISO or 'today'/'yesterday')")
    ep.add_argument("--end", help="End date")

    # -- analyze --
    ap = sub.add_parser("analyze", help="Time analysis")
    asub = ap.add_subparsers(dest="action")

    at = asub.add_parser("today", help="Today's summary")
    at.add_argument("--date", default="today", help="Date (default: today)")

    ar = asub.add_parser("range", help="Date range summary")
    ar.add_argument("--start", required=True)
    ar.add_argument("--end", required=True)
    ar.add_argument("--group-by", default="day", choices=["day", "app"])

    aa = asub.add_parser("app", help="App usage analysis")
    aa.add_argument("app_name", nargs="?", help="Specific app name")
    aa.add_argument("--days", type=int, default=7)

    asub.add_parser("focus", help="Find focus sessions").add_argument(
        "--min-minutes", type=int, default=30
    )
    asub.add_parser("productivity", help="Productivity report").add_argument(
        "--days", type=int, default=7
    )
    asub.add_parser("current", help="Current activity")
    apar = asub.add_parser("parallel", help="Parallel activities across streams")
    apar.add_argument("--start", help="Start datetime")
    apar.add_argument("--end", help="End datetime")
    apar.add_argument("--days", type=int, default=1, help="Days back (default 1)")

    # -- query --
    qp = sub.add_parser("query", help="Run queries")
    qsub = qp.add_subparsers(dest="action")
    qa = qsub.add_parser("aql", help="Run AQL query")
    qa.add_argument("query_str", help="AQL query string")
    qa.add_argument("--start", required=True)
    qa.add_argument("--end", required=True)
    qs = qsub.add_parser("sql", help="Run SQL query")
    qs.add_argument("sql_str", help="SQL query string")

    # -- project --
    pp = sub.add_parser("project", help="Project tracking")
    psub = pp.add_subparsers(dest="action")
    psub.add_parser("list", help="List projects")
    pd = psub.add_parser("define", help="Define a project")
    pd.add_argument("name", help="Project name")
    pd.add_argument("--rules", required=True, help="JSON rules")
    pdel = psub.add_parser("delete", help="Delete project")
    pdel.add_argument("name", help="Project name")
    pt = psub.add_parser("time", help="Get project time")
    pt.add_argument("name", help="Project name")
    pt.add_argument("--start", required=True)
    pt.add_argument("--end", required=True)
    ptag = psub.add_parser("tag", help="Tag time to project")
    ptag.add_argument("project", help="Project name")
    ptag.add_argument("--start", required=True)
    ptag.add_argument("--end", required=True)
    ptag.add_argument("--notes", help="Notes")

    # -- report --
    rp = sub.add_parser("report", help="Generate reports")
    rsub = rp.add_subparsers(dest="action")
    rd = rsub.add_parser("daily", help="Daily report")
    rd.add_argument("--date", default="today")
    rw = rsub.add_parser("weekly", help="Weekly report")
    rw.add_argument("--week-start", help="Week start date")
    rpr = rsub.add_parser("project", help="Project report")
    rpr.add_argument("name", help="Project name")
    rpr.add_argument("--start", required=True)
    rpr.add_argument("--end", required=True)
    rs = rsub.add_parser("story", help="Rich activity story with timeline")
    rs.add_argument("--date", default="today")
    rv = rsub.add_parser("visual", help="Visual HTML report with charts")
    rv.add_argument("--date", default="today")
    rv.add_argument("--output", help="Output file path")
    rv.add_argument("--open", action="store_true", default=True, help="Open in browser")

    # -- export --
    xp = sub.add_parser("export", help="Export data")
    xsub = xp.add_subparsers(dest="action")
    xr = xsub.add_parser("range", help="Export date range")
    xr.add_argument("--start", required=True)
    xr.add_argument("--end", required=True)
    xr.add_argument("--buckets", nargs="*", help="Bucket IDs")
    xr.add_argument("--format", default="json", choices=["json", "csv"])
    xsub.add_parser("all", help="Export everything")

    # -- server info --
    sub.add_parser("info", help="Server/database info")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    api = ActivityWatchAPI()
    output_format = args.output_format

    def out(data):
        if output_format == "json" or isinstance(data, (dict, list)):
            print(json.dumps(data, indent=2, default=str))
        else:
            print(data)

    if args.command == "info":
        out(api.get_server_info())

    elif args.command == "buckets":
        if args.action == "list":
            out(api.list_buckets())
        elif args.action == "info":
            out(api.get_bucket_info(args.bucket_id))

    elif args.command == "events":
        start = _parse_date_arg(args.start) + " 00:00:00" if args.start else None
        end = _parse_date_arg(args.end) + " 00:00:00" if args.end else None
        out(api.get_events(args.bucket_id, args.limit, start, end))

    elif args.command == "analyze":
        if args.action == "today":
            d = _parse_date_arg(args.date)
            summary = api.daily_summary(d)
            if output_format == "json":
                out(summary)
            else:
                out(api.generate_daily_report(d, "markdown"))
        elif args.action == "range":
            out(api.range_summary(
                args.start + " 00:00:00", args.end + " 00:00:00", args.group_by
            ))
        elif args.action == "app":
            out(api.app_usage(args.days, args.app_name))
        elif args.action == "focus":
            end_d = date.today() + timedelta(days=1)
            start_d = end_d - timedelta(days=7)
            out(api.find_focus_sessions(
                f"{start_d} 00:00:00", f"{end_d} 00:00:00", args.min_minutes
            ))
        elif args.action == "productivity":
            end_d = date.today() + timedelta(days=1)
            start_d = end_d - timedelta(days=args.days)
            out(api.productivity_report(
                f"{start_d} 00:00:00", f"{end_d} 00:00:00"
            ))
        elif args.action == "current":
            out(api.get_current_activity())
        elif args.action == "parallel":
            if args.start and args.end:
                out(api.parallel_activities(args.start, args.end))
            else:
                end_d = date.today() + timedelta(days=1)
                start_d = end_d - timedelta(days=args.days)
                out(api.parallel_activities(
                    f"{start_d} 00:00:00", f"{end_d} 00:00:00"
                ))

    elif args.command == "query":
        if args.action == "aql":
            out(api.run_aql_query(args.query_str, args.start, args.end))
        elif args.action == "sql":
            out(api.run_sql(args.sql_str))

    elif args.command == "project":
        if args.action == "list":
            out(api.list_projects())
        elif args.action == "define":
            out(api.define_project(args.name, json.loads(args.rules)))
        elif args.action == "delete":
            out(api.delete_project(args.name))
        elif args.action == "time":
            out(api.get_project_time(args.name, args.start + " 00:00:00", args.end + " 00:00:00"))
        elif args.action == "tag":
            out(api.tag_time(args.start, args.end, args.project, args.notes))

    elif args.command == "report":
        if args.action == "daily":
            d = _parse_date_arg(args.date)
            out(api.generate_daily_report(d, "markdown"))
        elif args.action == "weekly":
            out(api.generate_weekly_report(args.week_start, "markdown"))
        elif args.action == "project":
            out(api.generate_project_report(
                args.name, args.start + " 00:00:00", args.end + " 00:00:00", "markdown"
            ))
        elif args.action == "story":
            d = _parse_date_arg(args.date)
            out(api.generate_activity_story(d, output_format))
        elif args.action == "visual":
            d = _parse_date_arg(args.date)
            path = api.generate_html_report(d, args.output)
            print(f"Report saved to: {path}")
            if args.open:
                import subprocess
                subprocess.run(["open", path], check=False)

    elif args.command == "export":
        if args.action == "range":
            out(api.export_range(
                args.start + " 00:00:00", args.end + " 00:00:00",
                args.buckets, args.format
            ))
        elif args.action == "all":
            out(api.export_all())


if __name__ == "__main__":
    main()

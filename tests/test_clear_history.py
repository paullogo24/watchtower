"""History cleanup must preserve registrations and never partially clear data."""
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from sqlalchemy.exc import IntegrityError

from watchtower.storage.sqlite_event_store import SQLiteEventStore


ROOT = Path(__file__).resolve().parents[1]


class ClearHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "history.db"
        self.store = SQLiteEventStore(str(self.path))
        self.addCleanup(self.store.db.engine.dispose)
        with closing(sqlite3.connect(self.path)) as conn, conn:
            for device_id, active in (("active", 1), ("inactive", 0)):
                conn.execute(
                    "INSERT INTO devices (id, name, ip_address, hostname, device_type, "
                    "location, is_active, created_at, current_state, last_check, "
                    "last_latency_ms, consecutive_failures, consecutive_successes) "
                    "VALUES (?, ?, ?, ?, 'router', 'Lab', ?, '2026-01-01', "
                    "'down', '2026-01-02', 25.0, 3, 2)",
                    (device_id, device_id, "192.0.2.1" if active else "192.0.2.2", "router", active),
                )
                conn.execute("INSERT INTO checks (device_id, success) VALUES (?, 0)", (device_id,))
                conn.execute(
                    "INSERT INTO state_changes (device_id, old_state, new_state) VALUES (?, 'up', 'down')",
                    (device_id,),
                )
            conn.execute("INSERT INTO alerts (device_id, message) VALUES ('batch', 'Outage')")

    def snapshot(self):
        with closing(sqlite3.connect(self.path)) as conn:
            return {
                table: conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
                for table in ("devices", "checks", "state_changes", "alerts")
            }

    def run_cli(self, *args, answer=""):
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "manage.py"), "--db", str(self.path),
             "clear-history", *args],
            cwd=self.temp.name, input=answer, text=True, capture_output=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=15,
        )

    def assert_cleared(self, before):
        after = self.snapshot()
        # First eight columns are registration fields, including is_active and created_at.
        self.assertEqual([row[:8] for row in before["devices"]],
                         [row[:8] for row in after["devices"]])
        for row in after["devices"]:
            self.assertEqual(row[8:], ("unknown", None, None, 0, 0))
        for table in ("checks", "state_changes", "alerts"):
            self.assertEqual(after[table], [])

    def test_clear_preserves_active_and_inactive_devices_and_can_repeat(self):
        before = self.snapshot()
        self.assertEqual(self.store.clear_history(), {"checks": 2, "state_changes": 2, "alerts": 1})
        self.assert_cleared(before)
        self.assertEqual(self.store.clear_history(), {"checks": 0, "state_changes": 0, "alerts": 0})
        self.assert_cleared(before)

    def test_cli_decline_blank_and_eof_leave_database_unchanged(self):
        before = self.snapshot()
        for answer in ("n\n", "\n", ""):
            with self.subTest(answer=answer):
                result = self.run_cli(answer=answer)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Cancelled", result.stdout)
                self.assertEqual(self.snapshot(), before)

    def test_cli_confirmation(self):
        before = self.snapshot()
        result = self.run_cli(answer="y\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Cleared 2 checks, 2 state changes, and 1 alerts", result.stdout)
        self.assert_cleared(before)

    def test_cli_yes_uses_selected_database_only(self):
        default_path = Path(self.temp.name) / "data" / "watchtower.db"
        default_path.parent.mkdir()
        with closing(sqlite3.connect(self.path)) as source, closing(sqlite3.connect(default_path)) as dest:
            source.backup(dest)
        untouched = default_path.read_bytes()
        before = self.snapshot()
        result = self.run_cli("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_cleared(before)
        self.assertEqual(default_path.read_bytes(), untouched)

    def test_failure_during_status_reset_rolls_back_all_deletions(self):
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute(
                "CREATE TRIGGER reject_reset BEFORE UPDATE ON devices "
                "BEGIN SELECT RAISE(ABORT, 'simulated reset failure'); END"
            )
        before = self.snapshot()
        with self.assertRaises(IntegrityError):
            self.store.clear_history()
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()

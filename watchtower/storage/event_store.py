import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from dataclasses import asdict

from watchtower.models import CheckResult, StateChange, AlertLog


class EventStore:
    """Stores events to JSON lines files. Simple, human-readable, easy to parse."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.checks_file = self.data_dir / "checks.jsonl"
        self.states_file = self.data_dir / "state_changes.jsonl"
        self.alerts_file = self.data_dir / "alerts.jsonl"

    def _serialize(self, obj) -> dict:
        d = asdict(obj)
        # Convert enums and datetime
        for key, value in d.items():
            if hasattr(value, 'value'):
                d[key] = value.value
            elif isinstance(value, datetime):
                d[key] = value.isoformat()
        return d

    def log_check(self, result: CheckResult):
        """Log a ping check result."""
        with open(self.checks_file, "a") as f:
            f.write(json.dumps(self._serialize(result)) + "\n")

    def log_state_change(self, change: StateChange):
        """Log a device state change."""
        with open(self.states_file, "a") as f:
            f.write(json.dumps(self._serialize(change)) + "\n")

    def log_alert(self, alert: AlertLog):
        """Log an alert that was sent."""
        with open(self.alerts_file, "a") as f:
            f.write(json.dumps(self._serialize(alert)) + "\n")

    def get_recent_checks(self, device_id: str, limit: int = 100) -> List[dict]:
        """Get recent check results for a device."""
        results = []
        if not self.checks_file.exists():
            return results

        with open(self.checks_file, "r") as f:
            for line in f:
                data = json.loads(line.strip())
                if data.get("device_id") == device_id:
                    results.append(data)

        return results[-limit:]

    def get_recent_state_changes(self, device_id: Optional[str] = None, limit: int = 50) -> List[dict]:
        """Get recent state changes, optionally filtered by device."""
        results = []
        if not self.states_file.exists():
            return results

        with open(self.states_file, "r") as f:
            for line in f:
                data = json.loads(line.strip())
                if device_id is None or data.get("device_id") == device_id:
                    results.append(data)

        return results[-limit:]

    def get_all_events(self) -> dict:
        """Get counts of all stored events."""
        return {
            "checks": sum(1 for _ in open(self.checks_file)) if self.checks_file.exists() else 0,
            "state_changes": sum(1 for _ in open(self.states_file)) if self.states_file.exists() else 0,
            "alerts": sum(1 for _ in open(self.alerts_file)) if self.alerts_file.exists() else 0,
        }

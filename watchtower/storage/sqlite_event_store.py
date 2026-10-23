
# SQLite Event Store — Replaces JSON lines with queryable SQLite database.

from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy import func, and_

from watchtower.database import Database
from watchtower.models_sql import CheckResultDB, StateChangeDB, AlertLogDB, DeviceDB, DeviceState, AlertSeverity
from watchtower.models import CheckResult, StateChange, AlertLog, Device


class SQLiteEventStore:
    # Stores and queries events in SQLite.

    def __init__(self, db_path: str = "data/watchtower.db"):
        self.db = Database(db_path)
        self.db.create_tables()

    # === WRITE OPERATIONS ===

    def log_check(self, result: CheckResult):
        # Log a ping check result. 
        session = self.db.get_session()
        try:
            db_result = CheckResultDB(
                device_id=result.device_id,
                success=result.success,
                latency_ms=result.latency_ms,
                error_message=result.error_message,
                attempt_number=result.attempt_number
            )
            session.add(db_result)
            session.commit()
        finally:
            session.close()

    def log_state_change(self, change: StateChange):
        # Log a device state change.
        session = self.db.get_session()
        try:
            db_change = StateChangeDB(
                device_id=change.device_id,
                old_state=DeviceState(change.old_state.value),
                new_state=DeviceState(change.new_state.value),
                reason=change.reason,
                latency_ms=change.latency_ms
            )
            session.add(db_change)
            session.commit()
        finally:
            session.close()

    def log_alert(self, alert: AlertLog):
        # Log an alert that was sent.
        session = self.db.get_session()
        try:
            db_alert = AlertLogDB(
                device_id=alert.device_id,
                alert_type=alert.alert_type,
                severity=AlertSeverity(alert.severity.value),
                message=alert.message,
                sent_successfully=alert.sent_successfully,
                error=alert.error
            )
            session.add(db_alert)
            session.commit()
        finally:
            session.close()

    def update_device_status(self, device: Device) -> bool:
        """Save monitoring fields without changing or creating registrations.

        Skip deleted, inactive, or readdressed devices. The predicates and update
        run in one statement so registry changes cannot race a separate lookup.
        Return whether an eligible registration was updated.
        """
        with self.db.get_session() as session:
            with session.begin():
                updated = session.query(DeviceDB).filter_by(
                    id=device.id,
                    ip_address=device.ip_address,
                    is_active=True,
                ).update({
                    DeviceDB.current_state: DeviceState(device.current_state.value),
                    DeviceDB.last_latency_ms: device.last_latency_ms,
                    DeviceDB.last_check: device.last_check,
                    DeviceDB.consecutive_failures: device.consecutive_failures,
                    DeviceDB.consecutive_successes: device.consecutive_successes,
                }, synchronize_session=False)
            return updated > 0

    # === READ OPERATIONS ===

    def get_recent_checks(self, device_id: str, limit: int = 100) -> List[Dict]:
        # Get recent check results for a device.
        session = self.db.get_session()
        try:
            results = session.query(CheckResultDB)\
                .filter_by(device_id=device_id)\
                .order_by(CheckResultDB.timestamp.desc())\
                .limit(limit)\
                .all()
            return [
                {
                    "device_id": r.device_id,
                    "timestamp": r.timestamp.isoformat(),
                    "success": r.success,
                    "latency_ms": r.latency_ms,
                    "error_message": r.error_message,
                    "attempt_number": r.attempt_number
                }
                for r in results
            ]
        finally:
            session.close()

    def get_recent_state_changes(self, device_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        # Get recent state changes.
        session = self.db.get_session()
        try:
            query = session.query(StateChangeDB).order_by(StateChangeDB.timestamp.desc())
            if device_id:
                query = query.filter_by(device_id=device_id)
            results = query.limit(limit).all()
            return [
                {
                    "device_id": r.device_id,
                    "old_state": r.old_state.value,
                    "new_state": r.new_state.value,
                    "timestamp": r.timestamp.isoformat(),
                    "reason": r.reason,
                    "latency_ms": r.latency_ms
                }
                for r in results
            ]
        finally:
            session.close()

    # === READ OPERATIONS ===

    def get_all_events(self) -> Dict[str, int]:
        # Get counts of all stored events.
        session = self.db.get_session()
        try:
            checks = session.query(func.count(CheckResultDB.id)).scalar()
            state_changes = session.query(func.count(StateChangeDB.id)).scalar()
            alerts = session.query(func.count(AlertLogDB.id)).scalar()
            return {
                "checks": checks or 0,
                "state_changes": state_changes or 0,
                "alerts": alerts or 0
            }
        finally:
            session.close()

    # === CLEANUP ===

    def clear_history(self) -> Dict[str, int]:
        """Clear monitoring data and reset live status, preserving device registration.

        Stop the monitor before calling this so it cannot write stale state back.
        All changes commit together or roll back together.
        """
        with self.db.get_session() as session:
            with session.begin():
                counts = {
                    "checks": session.query(CheckResultDB).delete(synchronize_session=False),
                    "state_changes": session.query(StateChangeDB).delete(synchronize_session=False),
                    "alerts": session.query(AlertLogDB).delete(synchronize_session=False),
                }
                session.query(DeviceDB).update({
                    DeviceDB.current_state: DeviceState.unknown,
                    DeviceDB.last_check: None,
                    DeviceDB.last_latency_ms: None,
                    DeviceDB.consecutive_failures: 0,
                    DeviceDB.consecutive_successes: 0,
                }, synchronize_session=False)
            return counts

    def delete_old_events(self, days: int = 30):
        # Delete events older than N days.
        cutoff = datetime.utcnow() - timedelta(days=days)
        session = self.db.get_session()
        try:
            session.query(CheckResultDB).filter(CheckResultDB.timestamp < cutoff).delete()
            session.query(StateChangeDB).filter(StateChangeDB.timestamp < cutoff).delete()
            session.query(AlertLogDB).filter(AlertLogDB.timestamp < cutoff).delete()
            session.commit()
        finally:
            session.close()

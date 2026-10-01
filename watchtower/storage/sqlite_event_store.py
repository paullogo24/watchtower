
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

    def upsert_device(self, device: Device):
        # Insert or update device in database.  
        session = self.db.get_session()
        try:
            db_device = session.query(DeviceDB).filter_by(id=device.id).first()
            if db_device:
                db_device.name = device.name
                db_device.ip_address = device.ip_address
                db_device.hostname = device.hostname
                db_device.device_type = device.device_type
                db_device.location = device.location
                db_device.current_state = DeviceState(device.current_state.value)
                db_device.last_latency_ms = device.last_latency_ms
                db_device.last_check = device.last_check
            else:
                db_device = DeviceDB(
                    id=device.id,
                    name=device.name,
                    ip_address=device.ip_address,
                    hostname=device.hostname,
                    device_type=device.device_type,
                    location=device.location,
                    current_state=DeviceState(device.current_state.value),
                    last_latency_ms=device.last_latency_ms,
                    last_check=device.last_check
                )
                session.add(db_device)
            session.commit()
        finally:
            session.close()

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

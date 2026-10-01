"""
Queries — Historical data analysis and reporting.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import func, and_

from watchtower.database import Database
from watchtower.models_sql import CheckResultDB, StateChangeDB, DeviceDB, DeviceState


class Queries:
    """Query historical data for reports and analytics."""

    def __init__(self, db_path: str = "data/watchtower.db"):
        self.db = Database(db_path)

    def device_uptime(self, device_id: str, hours: int = 24) -> float:
        """Calculate device uptime percentage over last N hours."""
        session = self.db.get_session()
        try:
            since = datetime.utcnow() - timedelta(hours=hours)

            total = session.query(func.count(CheckResultDB.id))\
                .filter(and_(
                    CheckResultDB.device_id == device_id,
                    CheckResultDB.timestamp >= since
                )).scalar() or 0

            if total == 0:
                return 100.0

            successful = session.query(func.count(CheckResultDB.id))\
                .filter(and_(
                    CheckResultDB.device_id == device_id,
                    CheckResultDB.timestamp >= since,
                    CheckResultDB.success == True
                )).scalar() or 0

            return round((successful / total) * 100, 2)
        finally:
            session.close()

    def outage_history(self, device_id: Optional[str] = None, hours: int = 24) -> List[Dict]:
        """Get outage history (DOWN transitions) for a device or all devices."""
        session = self.db.get_session()
        try:
            since = datetime.utcnow() - timedelta(hours=hours)

            query = session.query(StateChangeDB)\
                .filter(and_(
                    StateChangeDB.new_state == DeviceState.down,
                    StateChangeDB.timestamp >= since
                ))\
                .order_by(StateChangeDB.timestamp.desc())

            if device_id:
                query = query.filter_by(device_id=device_id)

            results = query.all()
            return [
                {
                    "device_id": r.device_id,
                    "timestamp": r.timestamp.isoformat(),
                    "reason": r.reason,
                    "old_state": r.old_state.value
                }
                for r in results
            ]
        finally:
            session.close()

    def latency_trend(self, device_id: str, hours: int = 24) -> List[Dict]:
        """Get latency readings over time for graphing."""
        session = self.db.get_session()
        try:
            since = datetime.utcnow() - timedelta(hours=hours)

            results = session.query(CheckResultDB)\
                .filter(and_(
                    CheckResultDB.device_id == device_id,
                    CheckResultDB.timestamp >= since,
                    CheckResultDB.success == True
                ))\
                .order_by(CheckResultDB.timestamp.asc())\
                .all()

            return [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "latency_ms": r.latency_ms
                }
                for r in results
            ]
        finally:
            session.close()

    def all_devices_status(self) -> List[Dict]:
        """Get current status of all devices."""
        session = self.db.get_session()
        try:
            results = session.query(DeviceDB).order_by(DeviceDB.name).all()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "ip_address": r.ip_address,
                    "current_state": r.current_state.value,
                    "last_check": r.last_check.isoformat() if r.last_check else None,
                    "last_latency_ms": r.last_latency_ms
                }
                for r in results
            ]
        finally:
            session.close()

    def summary_report(self, hours: int = 24) -> Dict:
        """Generate a summary report of all monitoring activity."""
        session = self.db.get_session()
        try:
            since = datetime.utcnow() - timedelta(hours=hours)

            total_checks = session.query(func.count(CheckResultDB.id))\
                .filter(CheckResultDB.timestamp >= since).scalar() or 0

            failed_checks = session.query(func.count(CheckResultDB.id))\
                .filter(and_(
                    CheckResultDB.timestamp >= since,
                    CheckResultDB.success == False
                )).scalar() or 0

            state_changes = session.query(func.count(StateChangeDB.id))\
                .filter(StateChangeDB.timestamp >= since).scalar() or 0

            down_events = session.query(func.count(StateChangeDB.id))\
                .filter(and_(
                    StateChangeDB.timestamp >= since,
                    StateChangeDB.new_state == DeviceState.down
                )).scalar() or 0

            return {
                "period_hours": hours,
                "total_checks": total_checks,
                "failed_checks": failed_checks,
                "success_rate": round(((total_checks - failed_checks) / total_checks * 100), 2) if total_checks else 100.0,
                "state_changes": state_changes,
                "down_events": down_events
            }
        finally:
            session.close()

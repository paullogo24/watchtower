
# Device Registry — CRUD operations for monitored devices.
# Backed by the same SQLite `devices` table used for runtime state.
#python manage.py add --name "Main Router" --ip 192.168.1.1 --type router --location "Server Room" (for adding new devices)

from typing import List, Optional
from datetime import datetime

from watchtower.database import Database
from watchtower.models_sql import DeviceDB, DeviceState as DeviceStateDB
from watchtower.models import Device, DeviceState


class DeviceRegistry:
    # Add, remove, update, and list monitored devices in the database.

    def __init__(self, db_path: str = "data/watchtower.db"):
        self.db = Database(db_path)
        self.db.create_tables()

    # === CREATE ===

    def add_device(
        self,
        name: str,
        ip_address: str,
        hostname: str = "",
        device_type: str = "server",
        location: str = "",
    ) -> Device:
        #Add a new device to the registry. Returns the created Device.
        device = Device(
            name=name,
            ip_address=ip_address,
            hostname=hostname,
            device_type=device_type,
            location=location,
        )
        session = self.db.get_session()
        try:
            existing = session.query(DeviceDB).filter_by(ip_address=ip_address, is_active=True).first()
            if existing:
                raise ValueError(f"An active device with IP {ip_address} already exists ('{existing.name}')")

            db_device = DeviceDB(
                id=device.id,
                name=device.name,
                ip_address=device.ip_address,
                hostname=device.hostname,
                device_type=device.device_type,
                location=device.location,
                is_active=True,
                current_state=DeviceStateDB.unknown,
            )
            session.add(db_device)
            session.commit()
        finally:
            session.close()
        return device

    # === READ ===

    def list_devices(self, active_only: bool = True) -> List[Device]:
        # List all devices. Set active_only=False to include deactivated ones.
        session = self.db.get_session()
        try:
            query = session.query(DeviceDB)
            if active_only:
                query = query.filter_by(is_active=True)
            rows = query.order_by(DeviceDB.name).all()
            return [self._to_device(r) for r in rows]
        finally:
            session.close()

    def get_device(self, device_id: str) -> Optional[Device]:
        # Fetch a single device by id.
        session = self.db.get_session()
        try:
            row = session.query(DeviceDB).filter_by(id=device_id).first()
            return self._to_device(row) if row else None
        finally:
            session.close()

    # === UPDATE ===

    def update_device(self, device_id: str, **fields) -> Optional[Device]:
        #Update one or more fields on a device (name, ip_address, hostname, device_type, location).
        allowed = {"name", "ip_address", "hostname", "device_type", "location"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Cannot update unknown field(s): {', '.join(unknown)}")

        session = self.db.get_session()
        try:
            row = session.query(DeviceDB).filter_by(id=device_id).first()
            if not row:
                return None
            for key, value in fields.items():
                setattr(row, key, value)
            session.commit()
            return self._to_device(row)
        finally:
            session.close()

    # === DELETE (soft) ===

    def deactivate_device(self, device_id: str) -> bool:
        #Soft-delete: mark a device inactive so it stops being monitored but keeps its history.
        session = self.db.get_session()
        try:
            row = session.query(DeviceDB).filter_by(id=device_id).first()
            if not row:
                return False
            row.is_active = False
            session.commit()
            return True
        finally:
            session.close()

    def reactivate_device(self, device_id: str) -> bool:
        # Reverse a soft-delete.
        session = self.db.get_session()
        try:
            row = session.query(DeviceDB).filter_by(id=device_id).first()
            if not row:
                return False
            row.is_active = True
            session.commit()
            return True
        finally:
            session.close()

    def delete_device(self, device_id: str) -> bool:
        # Hard-delete a device row. History in checks/state_changes/alerts is kept (device_id just becomes orphaned)
        session = self.db.get_session()
        try:
            row = session.query(DeviceDB).filter_by(id=device_id).first()
            if not row:
                return False
            session.delete(row)
            session.commit()
            return True
        finally:
            session.close()

    # === HELPERS ===

    def _to_device(self, row: DeviceDB) -> Device:
        return Device(
            id=row.id,
            name=row.name,
            ip_address=row.ip_address,
            hostname=row.hostname or "",
            device_type=row.device_type or "server",
            location=row.location or "",
            is_active=row.is_active,
            created_at=row.created_at or datetime.utcnow(),
            current_state=DeviceState(row.current_state.value) if row.current_state else DeviceState.UNKNOWN,
            last_check=row.last_check,
            last_latency_ms=row.last_latency_ms,
            consecutive_failures=row.consecutive_failures or 0,
            consecutive_successes=row.consecutive_successes or 0,
        )

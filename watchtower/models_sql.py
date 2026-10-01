#SQLAlchemy Models — Database tables for WatchTower.

from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, Enum as SQLEnum
from sqlalchemy.sql import func
from watchtower.database import Base
import enum


class DeviceState(enum.Enum):
    up = "up"
    down = "down"
    degraded = "degraded"
    unknown = "unknown"


class AlertSeverity(enum.Enum):
    critical = "critical"
    warning = "warning"
    info = "info"


class DeviceDB(Base):
    #Monitored devices table.
    __tablename__ = "devices"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    hostname = Column(String)
    device_type = Column(String, default="server")
    location = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Runtime state (updated frequently)
    current_state = Column(SQLEnum(DeviceState), default=DeviceState.unknown)
    last_check = Column(DateTime)
    last_latency_ms = Column(Float)
    consecutive_failures = Column(Integer, default=0)
    consecutive_successes = Column(Integer, default=0)


class CheckResultDB(Base):
    #Every ping check result.
    __tablename__ = "checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, server_default=func.now())
    success = Column(Boolean, nullable=False)
    latency_ms = Column(Float)
    error_message = Column(String)
    attempt_number = Column(Integer, default=1)


class StateChangeDB(Base):
    # Device state transitions.
    __tablename__ = "state_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, nullable=False, index=True)
    old_state = Column(SQLEnum(DeviceState), nullable=False)
    new_state = Column(SQLEnum(DeviceState), nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    reason = Column(String)
    latency_ms = Column(Float)


class AlertLogDB(Base):
    # Alerts that were sent.
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, nullable=False, index=True)
    alert_type = Column(String, default="email")
    severity = Column(SQLEnum(AlertSeverity), default=AlertSeverity.info)
    message = Column(String)
    timestamp = Column(DateTime, server_default=func.now())
    sent_successfully = Column(Boolean, default=False)
    error = Column(String)

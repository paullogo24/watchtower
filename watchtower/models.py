"""
WatchTower Data Models
Core entities: Device, MonitoringConfig, CheckResult, StateChange, AlertLog
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class DeviceState(Enum):
    """Device health states."""
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"  # High latency but responding
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Device:
    """A network device to monitor."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    ip_address: str = ""
    hostname: str = ""
    device_type: str = "server"  # router, switch, server, printer, other
    location: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Runtime state (not persisted)
    current_state: DeviceState = DeviceState.UNKNOWN
    last_check: Optional[datetime] = None
    last_latency_ms: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    uptime_percentage: float = 100.0


@dataclass
class MonitoringConfig:
    """Per-device monitoring configuration."""
    device_id: str = ""
    ping_interval_sec: int = 60
    timeout_sec: float = 2.0
    retry_count: int = 3
    latency_threshold_ms: int = 100
    consecutive_failures_before_alert: int = 2
    consecutive_successes_before_recovery: int = 2


@dataclass
class CheckResult:
    """Result of a single ping check."""
    device_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = False
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    attempt_number: int = 1


@dataclass
class StateChange:
    """Record of a device state transition."""
    device_id: str = ""
    old_state: DeviceState = DeviceState.UNKNOWN
    new_state: DeviceState = DeviceState.UNKNOWN
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reason: str = ""  # e.g., "3 consecutive ping failures"
    latency_ms: Optional[float] = None


@dataclass
class AlertLog:
    """Record of an alert that was sent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    device_id: str = ""
    alert_type: str = "email"  # email, sms, webhook, dashboard
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sent_successfully: bool = False
    error: Optional[str] = None

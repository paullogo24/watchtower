import time
import threading
import schedule
from typing import List, Dict, Optional, Callable
from datetime import datetime

from watchtower.models import Device, MonitoringConfig, CheckResult, StateChange
from watchtower.monitor.ping_worker import PingWorker
from watchtower.monitor.state_manager import StateManager
from watchtower.storage.event_store import EventStore


class MonitorEngine:
    """
    Core monitoring engine that runs periodic health checks.
    """

    def __init__(self, event_store: Optional[EventStore] = None):
        self.devices: Dict[str, Device] = {}          # device_id - Device
        self.configs: Dict[str, MonitoringConfig] = {} # device_id - Config
        self.workers: Dict[str, PingWorker] = {}       # device_id - Worker
        self.state_managers: Dict[str, StateManager] = {} # device_id - StateManager

        self.event_store = event_store or EventStore()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Callbacks for external systems (alerts, dashboard)
        self._state_change_callbacks: List[Callable[[StateChange, Device], None]] = []
        self._check_callbacks: List[Callable[[CheckResult, Device], None]] = []

    def on_state_change(self, callback: Callable[[StateChange, Device], None]):
        """Register callback: called when any device changes state."""
        self._state_change_callbacks.append(callback)

    def on_check(self, callback: Callable[[CheckResult, Device], None]):
        """Register callback: called after every check (success or fail)."""
        self._check_callbacks.append(callback)

    def add_device(self, device: Device, config: Optional[MonitoringConfig] = None):
        """Add a device to monitoring."""
        if config is None:
            config = MonitoringConfig(device_id=device.id)
        else:
            config.device_id = device.id

        with self._lock:
            self.devices[device.id] = device
            self.configs[device.id] = config
            self.workers[device.id] = PingWorker(
                timeout=config.timeout_sec,
                retry_count=config.retry_count
            )
            self.state_managers[device.id] = StateManager(
                consecutive_failures_before_alert=config.consecutive_failures_before_alert,
                consecutive_successes_before_recovery=config.consecutive_successes_before_recovery,
                latency_threshold_ms=config.latency_threshold_ms
            )

            # Wire state manager to forward changes to engine callbacks
            self.state_managers[device.id].on_state_change(
                lambda change: self._handle_state_change(change, device)
            )

            # Schedule the check job
            schedule.every(config.ping_interval_sec).seconds.do(
                self._run_check, device_id=device.id
            )

        print(f"[MonitorEngine] Added device: {device.name} ({device.ip_address}) — check every {config.ping_interval_sec}s")

    def remove_device(self, device_id: str):
        """Remove a device from monitoring."""
        with self._lock:
            if device_id in self.devices:
                del self.devices[device_id]
                del self.configs[device_id]
                del self.workers[device_id]
                del self.state_managers[device_id]
                # Note: schedule.clear() would erase ALL jobs; 
                # for now we just stop tracking the device

    def _run_check(self, device_id: str):
        """Execute a single check for a device."""
        with self._lock:
            device = self.devices.get(device_id)
            if not device or not device.is_active:
                return
            worker = self.workers[device_id]
            state_manager = self.state_managers[device_id]

        result = worker.check(device)

        # Log the check
        self.event_store.log_check(result)

        # Process state change
        change = state_manager.process_check(device, result)

        # Notify check callbacks
        for callback in self._check_callbacks:
            callback(result, device)

        # Log state change if it happened
        if change:
            self.event_store.log_state_change(change)

    def _handle_state_change(self, change: StateChange, device: Device):
        """Internal handler that forwards to external callbacks."""
        for callback in self._state_change_callbacks:
            callback(change, device)

    def _scheduler_loop(self):
        """Background process that runs the schedule."""
        while self._running:
            schedule.run_pending()
            time.sleep(1)

    def start(self):
        """Start the monitoring engine in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        print(f"[MonitorEngine] Started — monitoring {len(self.devices)} device(s)")

    def stop(self):
        """Stop the monitoring engine."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        schedule.clear()
        print("[MonitorEngine] Stopped")

    def get_device_status(self, device_id: str) -> Optional[Device]:
        """Get current status of a device."""
        with self._lock:
            return self.devices.get(device_id)

    def get_all_devices(self) -> List[Device]:
        """Get all monitored devices."""
        with self._lock:
            return list(self.devices.values())

    def force_check(self, device_id: str) -> CheckResult:
        """Force an immediate check for a device."""
        self._run_check(device_id)
        # Return the most recent check from the event store
        recent = self.event_store.get_recent_checks(device_id, limit=1)
        if recent:
            r = recent[0]
            return CheckResult(
                device_id=r["device_id"],
                success=r["success"],
                latency_ms=r.get("latency_ms"),
                error_message=r.get("error_message"),
                attempt_number=r.get("attempt_number", 1)
            )
        return CheckResult(device_id=device_id, success=False, error_message="No check performed")

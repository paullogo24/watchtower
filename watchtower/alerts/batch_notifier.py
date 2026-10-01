"""
Batch Alert Notifier — Collects state changes and sends one batched email.
Uses a timer-based approach: collects changes for X seconds, then sends one email.
"""
import threading
import time
from typing import Optional, List, Callable
from datetime import datetime

from watchtower.models import StateChange, Device, AlertLog
from watchtower.config import Config
from watchtower.storage.event_store import EventStore
from watchtower.alerts.deduplicator import AlertDeduplicator
from watchtower.alerts.batch_email_alert import BatchEmailAlert


class BatchAlertNotifier:
    """
    Batched alert notifier. Collects state changes over a time window
    and sends a single consolidated email with all changes + full status.

    Usage:
        notifier = BatchAlertNotifier(batch_window_sec=60)
        engine.on_state_change(notifier.handle_state_change)
        # Changes are collected and sent as one email every 60 seconds
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        event_store: Optional[EventStore] = None,
        batch_window_sec: int = 60
    ):
        self.config = config or Config()
        self.event_store = event_store or EventStore()
        self.batch_window_sec = batch_window_sec

        # Deduplication (still useful for individual changes)
        dedup_window = self.config.get("alerts", "deduplication_window_sec", default=300)
        self.deduplicator = AlertDeduplicator(window_sec=dedup_window)

        # Email sender
        self.batch_email = BatchEmailAlert(config=self.config)

        # Batch collection
        self._batch_lock = threading.Lock()
        self._pending_changes: List[tuple] = []  # (change, device) tuples
        self._all_devices: List[Device] = []

        # Callbacks
        self._callbacks: List[Callable[[AlertLog], None]] = []

        # Timer for batch sending
        self._timer: Optional[threading.Timer] = None
        self._running = False

    def on_alert(self, callback: Callable[[AlertLog], None]):
        """Register callback for when batch alert is sent."""
        self._callbacks.append(callback)

    def handle_state_change(self, change: StateChange, device: Device):
        """
        Main entry point: called on every state change.
        Adds to batch and starts/extends the batch timer.
        """
        # Check deduplication
        should_send, reason = self.deduplicator.should_alert(change)

        if not should_send:
            alert = AlertLog(
                device_id=device.id,
                alert_type="suppressed",
                message=f"Alert suppressed: {reason}",
                sent_successfully=False
            )
            self.event_store.log_alert(alert)
            return alert

        # Add to batch
        with self._batch_lock:
            self._pending_changes.append((change, device))
            # Update device reference for full status table
            existing = next((d for d in self._all_devices if d.id == device.id), None)
            if existing:
                existing.current_state = device.current_state
                existing.last_latency_ms = device.last_latency_ms
            else:
                self._all_devices.append(device)

        # Start or reset timer
        self._reset_timer()

        return None  # Alert will be sent when batch timer fires

    def _reset_timer(self):
        """Reset the batch timer."""
        if self._timer:
            self._timer.cancel()

        self._timer = threading.Timer(self.batch_window_sec, self._send_batch)
        self._timer.daemon = True
        self._timer.start()

    def _send_batch(self):
        """Send the batched email."""
        with self._batch_lock:
            changes = self._pending_changes.copy()
            devices = list(self._all_devices)
            self._pending_changes.clear()

        if not changes:
            return

        # Add all changes to email batch
        for change, device in changes:
            self.batch_email.add_to_batch(change, device)

        # Send the email
        alert = self.batch_email.send_batch(devices)
        self.event_store.log_alert(alert)

        # Notify callbacks
        for callback in self._callbacks:
            callback(alert)

        # Print status
        if alert.sent_successfully:
            print(f"\n📧 BATCH ALERT SENT: {alert.message}")
        else:
            print(f"\n⚠️  BATCH ALERT FAILED: {alert.message}")
            if alert.error:
                print(f"    Error: {alert.error}")

    def force_send(self) -> Optional[AlertLog]:
        """Force send the current batch immediately."""
        if self._timer:
            self._timer.cancel()
        self._send_batch()
        return None

    def get_pending_count(self) -> int:
        """Get number of pending changes in current batch."""
        with self._batch_lock:
            return len(self._pending_changes)

    def get_dedup_stats(self) -> dict:
        """Get deduplication statistics."""
        return self.deduplicator.get_stats()

    def stop(self):
        """Stop the notifier and send any pending batch."""
        if self._timer:
            self._timer.cancel()
        self._send_batch()

from typing import Optional, Callable, List
from dataclasses import dataclass, field

from watchtower.models import Device, DeviceState, CheckResult, StateChange


class StateManager:
    """
    Manages device state machine with hysteresis.

    Rules:
    - UP -> DEGRADED: latency > threshold
    - UP -> DOWN: consecutive_failures >= threshold
    - DEGRADED -> DOWN: consecutive_failures >= threshold
    - DOWN -> UP: consecutive_successes >= threshold
    - DEGRADED -> UP: consecutive_successes >= threshold AND latency <= threshold
    """

    def __init__(
        self,
        consecutive_failures_before_alert: int = 2,
        consecutive_successes_before_recovery: int = 2,
        latency_threshold_ms: int = 100
    ):
        self.failure_threshold = consecutive_failures_before_alert
        self.recovery_threshold = consecutive_successes_before_recovery
        self.latency_threshold = latency_threshold_ms
        self._state_change_callbacks: List[Callable[[StateChange], None]] = []

    def on_state_change(self, callback: Callable[[StateChange], None]):
        """Register a callback to be called on every state change."""
        self._state_change_callbacks.append(callback)

    def process_check(self, device: Device, result: CheckResult) -> Optional[StateChange]:
        """
        Process a check result and update device state.
        Returns StateChange if state changed, None otherwise.
        """
        old_state = device.current_state

        if result.success:
            device.consecutive_successes += 1
            device.consecutive_failures = 0
            device.last_latency_ms = result.latency_ms
            device.last_check = result.timestamp

            # Check if latency is high
            is_degraded = result.latency_ms is not None and result.latency_ms > self.latency_threshold

            if old_state == DeviceState.DOWN:
                # Coming back from DOWN — need enough consecutive successes
                if device.consecutive_successes >= self.recovery_threshold:
                    device.current_state = DeviceState.UP
                # else: stay DOWN
            elif old_state == DeviceState.DEGRADED:
                if not is_degraded and device.consecutive_successes >= self.recovery_threshold:
                    device.current_state = DeviceState.UP
                elif is_degraded:
                    device.current_state = DeviceState.DEGRADED  # stay degraded
                # else: stay degraded until enough good pings
            else:  # UP or UNKNOWN
                if is_degraded:
                    device.current_state = DeviceState.DEGRADED
                else:
                    device.current_state = DeviceState.UP
        else:
            # Ping failed
            device.consecutive_failures += 1
            device.consecutive_successes = 0
            device.last_check = result.timestamp

            if old_state in (DeviceState.UP, DeviceState.DEGRADED, DeviceState.UNKNOWN):
                if device.consecutive_failures >= self.failure_threshold:
                    device.current_state = DeviceState.DOWN
                elif old_state == DeviceState.UP and device.consecutive_failures == 1:
                    # First failure — could be transient, stay UP for now
                    pass
                # else: stay in current state
            # If already DOWN, stay DOWN

        # Check if state actually changed
        if device.current_state != old_state:
            reason = self._build_reason(device, result, old_state)
            change = StateChange(
                device_id=device.id,
                old_state=old_state,
                new_state=device.current_state,
                reason=reason,
                latency_ms=result.latency_ms
            )

            # Notify all callbacks
            for callback in self._state_change_callbacks:
                callback(change)

            return change

        return None

    def _build_reason(self, device: Device, result: CheckResult, old_state: DeviceState) -> str:
        """Build a human-readable reason for the state change."""
        if device.current_state == DeviceState.DOWN:
            return f"{device.consecutive_failures} consecutive ping failures"
        elif device.current_state == DeviceState.UP:
            if old_state == DeviceState.DOWN:
                return f"{device.consecutive_successes} consecutive successful pings"
            elif old_state == DeviceState.DEGRADED:
                return f"Latency recovered to {result.latency_ms}ms"
            else:
                return "Device is responding"
        elif device.current_state == DeviceState.DEGRADED:
            return f"High latency detected: {result.latency_ms}ms (threshold: {self.latency_threshold}ms)"
        return "State changed"

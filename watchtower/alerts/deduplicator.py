#prevents spam by suppressing duplicate alerts
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field

from watchtower.models import StateChange, DeviceState


@dataclass
class AlertKey:
    
    device_id: str
    new_state: str
    
    def __hash__(self):
        return hash((self.device_id, self.new_state))
    
    def __eq__(self, other):
        if isinstance(other, AlertKey):
            return self.device_id == other.device_id and self.new_state == other.new_state
        return False


@dataclass
class AlertRecord:
    #Record of when an alert was last sent
    timestamp: float
    count: int = 1


class AlertDeduplicator:
    
    #Prevents duplicate alerts for the same device/state combination.
    
    #Rules:
    #- First alert for a device/state is always sent
    #- Subsequent alerts for same device/state are suppressed for window_sec
    #- After window expires, next alert is sent and window resets
    #- Recovery alerts (DOWN→UP) are always sent immediately
    
    
    def __init__(self, window_sec: int = 300):
        self.window_sec = window_sec
        self._sent_alerts: Dict[AlertKey, AlertRecord] = {}
    
    def should_alert(self, change: StateChange) -> Tuple[bool, str]:
        key = AlertKey(change.device_id, change.new_state.value)
        now = time.time()
        
        # Recovery alerts (DOWN→UP) are always sent
        if change.new_state == DeviceState.UP and change.old_state == DeviceState.DOWN:
            self._record_alert(key, now)
            return True, "Recovery alert — always sent"
        
        if key in self._sent_alerts:
            record = self._sent_alerts[key]
            elapsed = now - record.timestamp
            if elapsed < self.window_sec:
                remaining = self.window_sec - elapsed
                return False, f"Suppressed — {remaining:.0f}s remaining in dedup window"
            else:
                self._record_alert(key, now)
                return True, f"Window expired ({elapsed:.0f}s ago), resending"
        
        self._record_alert(key, now)
        return True, "First alert for this device/state"
    
    def _record_alert(self, key: AlertKey, timestamp: float):
        if key in self._sent_alerts:
            self._sent_alerts[key].timestamp = timestamp
            self._sent_alerts[key].count += 1
        else:
            self._sent_alerts[key] = AlertRecord(timestamp=timestamp)
    
    def get_stats(self) -> Dict[str, any]:
        now = time.time()
        active_windows = sum(
            1 for record in self._sent_alerts.values()
            if now - record.timestamp < self.window_sec
        )
        total_alerts = sum(record.count for record in self._sent_alerts.values())
        return {
            "tracked_combinations": len(self._sent_alerts),
            "active_suppression_windows": active_windows,
            "total_alerts_sent": total_alerts,
            "window_sec": self.window_sec,
        }
    
    def reset(self):
        self._sent_alerts.clear()
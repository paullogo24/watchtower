#Wires together deduplication, email alerts, and event logging.

from typing import Optional, List, Callable

from watchtower.models import StateChange, Device, AlertLog
from watchtower.config import Config
from watchtower.storage.event_store import EventStore
from watchtower.alerts.deduplicator import AlertDeduplicator
from watchtower.alerts.email_alert import EmailAlert


class AlertNotifier:
   
    def __init__(
        self,
        config: Optional[Config] = None,
        event_store: Optional[EventStore] = None
    ):
        self.config = config or Config()
        self.event_store = event_store or EventStore()
        
        dedup_window = self.config.get("alerts", "deduplication_window_sec", default=300)
        self.deduplicator = AlertDeduplicator(window_sec=dedup_window)
        
        self.email_alert = EmailAlert(config=self.config)
        
        self._callbacks: List[Callable[[AlertLog, StateChange, Device], None]] = []
    
    def on_alert(self, callback: Callable[[AlertLog, StateChange, Device], None]):
       
        self._callbacks.append(callback)
    
    def handle_state_change(self, change: StateChange, device: Device) -> AlertLog:
        
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
        
        alert = self.email_alert.send_alert(change, device)
        self.event_store.log_alert(alert)
        
        for callback in self._callbacks:
            callback(alert, change, device)
        
        return alert
    
    def get_dedup_stats(self) -> dict:
        return self.deduplicator.get_stats()
    
    def reset_dedup(self):
        self.deduplicator.reset()
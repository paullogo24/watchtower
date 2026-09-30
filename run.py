#WatchTower Monitor Engine — Test Runner

import time
import sys
from datetime import datetime

# Add watchtower to path
sys.path.insert(0, ".")

from watchtower.models import Device, MonitoringConfig, DeviceState
from watchtower.monitor.engine import MonitorEngine
from watchtower.storage.event_store import EventStore
from watchtower.alerts.notifier import AlertNotifier
from watchtower.config import Config
from watchtower.alerts.batch_notifier import BatchAlertNotifier
from watchtower.storage.sqlite_event_store import SQLiteEventStore
from watchtower.storage.queries import Queries


def print_report(queries, devices):
    """Print the current device status and the recent monitoring summary."""
    print("\n" + "=" * 60)
    print("MONITORING REPORT")
    print("=" * 60)

    for device in queries.all_devices_status():
        print(
            f"  {device['name']:25s} | {device['current_state']:10s} | "
            f"{device['last_latency_ms'] or 'N/A'}ms"
        )

    summary = queries.summary_report(hours=24)
    print("\nLast 24 hours:")
    print(f"  Total checks:  {summary['total_checks']}")
    print(f"  Failed checks: {summary['failed_checks']}")
    print(f"  Success rate:  {summary['success_rate']}%")
    print(f"  State changes: {summary['state_changes']}")
    print(f"  Down events:   {summary['down_events']}")



def print_banner():
    print("=" * 60)
    print("   🗼  WATCHTOWER — Monitor Engine Test")
    print("=" * 60)
    print()


def on_state_change(change, device):
    """Callback: called when device state changes."""
    emoji = {
        DeviceState.UP: "🟢",
        DeviceState.DOWN: "🔴",
        DeviceState.DEGRADED: "🟡",
        DeviceState.UNKNOWN: "⚪"
    }.get(change.new_state, "❓")

    print(f"\n{emoji} STATE CHANGE: {device.name}")
    print(f"   {change.old_state.value} → {change.new_state.value}")
    print(f"   Reason: {change.reason}")
    print(f"   Time: {change.timestamp.strftime('%H:%M:%S')}")
    print()


def on_check(result, device):
    """Callback: called after every check."""
    status = "✅" if result.success else "❌"
    latency = f"{result.latency_ms:.1f}ms" if result.latency_ms else "N/A"
    print(f"  {status} {device.name:20s} | {latency:>8s} | attempt {result.attempt_number}/{3}")


def on_alert(alert, *args):
    if alert.alert_type == "suppressed":
        print(f"   📭 SUPPRESSED: {alert.message}")
    elif alert.sent_successfully:
        print(f"   📧 ALERT SENT: {alert.message}")
    else:
        print(f"   ⚠️  ALERT FAILED: {alert.message}")
        if alert.error:
            print(f"      Error: {alert.error}")


def main():
    print_banner()

    config = Config("config.yaml")

    #User sqlite instead of json
    store = SQLiteEventStore(db_path="data/watchtower.db")
    queries = Queries(db_path="data/watchtower.db")

    engine = MonitorEngine(event_store=store)

    # Setup alerts
    notifier = BatchAlertNotifier(config=config, event_store=store, batch_window_sec=60)
    notifier.on_alert(on_alert)
    engine.on_state_change(lambda change, device: notifier.handle_state_change(change, device))
    engine.on_check(on_check)
    

    # Add test devices
    devices = [
        Device(
            name="Localhost",
            ip_address="127.0.0.1",
            hostname="localhost",
            device_type="server",
            location="Local"
        ),
        Device(
            name="Google DNS",
            ip_address="8.8.8.8",
            hostname="dns.google",
            device_type="server",
            location="External"
        ),
        Device(
            name="Fake Device",
            ip_address="192.0.2.1",
            hostname="fake-device",
            device_type="server",
            location="N/A"
        ),
        Device(
            name="Cloudflare DNS",
            ip_address="1.1.1.1",
            hostname="cloudflare-dns",
            device_type="server",
            location="External"
        ),
        Device(
            name="My Phone",
            ip_address="172.27.108.211",
            hostname="myphone",
            device_type="personaldevice",
            location="External"
        )
    ]

    # Config
    monitor_config = MonitoringConfig(
        ping_interval_sec= 30,
        timeout_sec=2.0,
        retry_count=3,
        latency_threshold_ms=50,
        consecutive_failures_before_alert=3,
        consecutive_successes_before_recovery=2
    )

    print("Registering devices...")
    for device in devices:
        engine.add_device(device, monitor_config)

    print(f"\nStarting monitor — will run for 180 seconds...")
    print("-" * 60)
    engine.start()

    try:
        for i in range(180):
            time.sleep(1)
            if i % 30 == 0 and i > 0:
                print(f"\n--- Summary at {i}s ---")
                for d in engine.get_all_devices():
                    state_emoji = {
                        DeviceState.UP: "🟢",
                        DeviceState.DOWN: "🔴",
                        DeviceState.DEGRADED: "🟡",
                        DeviceState.UNKNOWN: "⚪"
                    }.get(d.current_state, "❓")
                    latency = f"{d.last_latency_ms:.1f}ms" if d.last_latency_ms else "N/A"
                    print(f"  {state_emoji} {d.name:25s} | {d.current_state.value:10s} | {latency:>8s}")
                print()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")

    notifier.stop()
    engine.stop()

    # update device states in DB
    for d in engine.get_all_devices():
        store.upsert_device(d)

    # print sqlite report
    print_report(queries, devices)

    # Event counts
    print("\n" + "=" * 60)
    print("DATABASE STATS")
    print("=" * 60)
    events = store.get_all_events()
    print(f"Total checks:     {events['checks']}")
    print(f"State changes:    {events['state_changes']}")
    print(f"Alerts sent:      {events['alerts']}")
    
    print("\n✅ Monitor engine test complete!")
    print("Database file: data/watchtower.db")

if __name__ == "__main__":
    main()
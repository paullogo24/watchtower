#!/usr/bin/env python3
"""
WatchTower Batch Alert Demo — One email with all device changes.
Collects state changes for 60 seconds, then sends one consolidated email.
"""
import time
import sys
from datetime import datetime

sys.path.insert(0, ".")

from watchtower.models import Device, MonitoringConfig, DeviceState
from watchtower.monitor.engine import MonitorEngine
from watchtower.storage.event_store import EventStore
from watchtower.alerts.batch_notifier import BatchAlertNotifier
from watchtower.config import Config


def print_banner():
    print("=" * 60)
    print("   🗼  WATCHTOWER — Batch Alert System Demo")
    print("   One email with all device changes")
    print("=" * 60)
    print()


def on_check(result, device):
    status = "✅" if result.success else "❌"
    latency = f"{result.latency_ms:.1f}ms" if result.latency_ms else "N/A"
    print(f"  {status} {device.name:25s} | {latency:>8s} | {device.current_state.value:10s}")


def on_alert(alert):
    """Called when batch email is sent."""
    if alert.sent_successfully:
        print(f"\n📧 BATCH EMAIL SENT: {alert.message}")
    else:
        print(f"\n⚠️  BATCH EMAIL FAILED: {alert.message}")
        if alert.error:
            print(f"    Error: {alert.error}")


def main():
    print_banner()

    config = Config("config.yaml")
    store = EventStore(data_dir=config.get("storage", "data_dir", default="data"))
    engine = MonitorEngine(event_store=store)

    # Batch notifier: collects changes for 60 seconds, sends one email
    notifier = BatchAlertNotifier(
        config=config,
        event_store=store,
        batch_window_sec=60  # One email per minute
    )
    notifier.on_alert(on_alert)

    # Wire batch alerts to state changes
    engine.on_state_change(lambda change, device: notifier.handle_state_change(change, device))
    engine.on_check(on_check)

    # Test devices
    devices = [
        Device(name="Localhost", ip_address="127.0.0.1", hostname="localhost", device_type="server", location="Local"),
        Device(name="Google DNS", ip_address="8.8.8.8", hostname="dns.google", device_type="server", location="External"),
        Device(name="Fake Device", ip_address="192.0.2.1", hostname="fake-device", device_type="server", location="N/A"),
        Device(name="Cloudflare DNS", ip_address="1.1.1.1", hostname="cloudflare-dns", device_type="server", location="External"),
    ]

    monitor_config = MonitoringConfig(
        ping_interval_sec=10,
        timeout_sec=2.0,
        retry_count=2,
        latency_threshold_ms=50,
        consecutive_failures_before_alert=2,
        consecutive_successes_before_recovery=2
    )

    print("Registering devices...")
    for device in devices:
        engine.add_device(device, monitor_config)

    print(f"\nStarting monitor — batch emails every 60 seconds...")
    print("-" * 60)
    engine.start()

    try:
        for i in range(180):  # Run for 3 minutes
            time.sleep(1)
            if i % 30 == 0 and i > 0:
                pending = notifier.get_pending_count()
                print(f"\n--- Summary at {i}s (pending changes: {pending}) ---")
                for d in engine.get_all_devices():
                    emoji = {"up": "🟢", "down": "🔴", "degraded": "🟡", "unknown": "⚪"}.get(d.current_state.value, "❓")
                    latency = f"{d.last_latency_ms:.1f}ms" if d.last_latency_ms else "N/A"
                    print(f"  {emoji} {d.name:25s} | {d.current_state.value:10s} | {latency:>8s}")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")

    notifier.stop()  # Send any pending batch
    engine.stop()

    print("\n" + "=" * 60)
    print("FINAL REPORT")
    print("=" * 60)
    events = store.get_all_events()
    print(f"Total checks:     {events['checks']}")
    print(f"State changes:    {events['state_changes']}")
    print(f"Alerts sent:      {events['alerts']}")
    print("\n✅ Batch alert demo complete!")


if __name__ == "__main__":
    main()

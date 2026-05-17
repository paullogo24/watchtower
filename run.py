"""
WatchTower Monitor Engine — Test Runner
"""
import time
import sys
from datetime import datetime

# Add watchtower to path
sys.path.insert(0, ".")

from watchtower.models import Device, MonitoringConfig, DeviceState
from watchtower.monitor.engine import MonitorEngine
from watchtower.storage.event_store import EventStore


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


def main():
    print_banner()

    # Create event store
    store = EventStore(data_dir="data")

    # Create engine
    engine = MonitorEngine(event_store=store)
    engine.on_state_change(on_state_change)
    engine.on_check(on_check)

    # Add test devices
    # NOTE: Replace these with IPs in your network, or use loopback for testing
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
            ip_address="192.0.2.1",  # non-routable IP address
            hostname="fake-device",
            device_type="server",
            location="Nowhere"
        ),
    ]

    # Config: check every 10 seconds for demo (production: 60s)
    config = MonitoringConfig(
        ping_interval_sec=10,
        timeout_sec=2.0,
        retry_count=3,
        latency_threshold_ms=50,  # Low threshold to easily trigger DEGRADED
        consecutive_failures_before_alert=2,
        consecutive_successes_before_recovery=2
    )

    print("Registering devices...")
    for device in devices:
        engine.add_device(device, config)

    print(f"\nStarting monitor — will run for 60 seconds...")
    print("-" * 60)
    engine.start()

    try:
        # Run for 60 seconds
        for i in range(60):
            time.sleep(1)
            if i % 10 == 0 and i > 0:
                # Print summary every 10 seconds
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
        print("Interrupted by user.")

    engine.stop()

    # Print final stats
    print("\n" + "=" * 60)
    print("FINAL REPORT")
    print("=" * 60)
    events = store.get_all_events()
    print(f"Total checks logged:    {events['checks']}")
    print(f"Total state changes:    {events['state_changes']}")
    print(f"Total alerts logged:    {events['alerts']}")

    print("Device final states:")
    for d in engine.get_all_devices():
        print(f"  {d.name}: {d.current_state.value} (uptime: {d.uptime_percentage:.1f}%)")

    print("\nRecent state changes:")
    changes = store.get_recent_state_changes(limit=10)
    for c in changes:
        print(f"  [{c['timestamp']}] {c['device_id']}: {c['old_state']} → {c['new_state']} | {c['reason']}")

    print("\n✅ Monitor engine test complete!")


if __name__ == "__main__":
    main()

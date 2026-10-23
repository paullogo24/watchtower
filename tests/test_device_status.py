"""A stale monitor copy must never overwrite registry edits or recreate devices."""
from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from watchtower.models import Device, DeviceState
from watchtower.storage.device_registry import DeviceRegistry
from watchtower.storage.sqlite_event_store import SQLiteEventStore


class DeviceStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path = str(Path(self.temp.name) / "devices.db")
        self.registry = DeviceRegistry(path)
        self.store = SQLiteEventStore(path)
        self.addCleanup(self.registry.db.engine.dispose)
        self.addCleanup(self.store.db.engine.dispose)
        registered = self.registry.add_device(
            name="Main Router", ip_address="192.0.2.1", hostname="main",
            device_type="router", location="Server Room",
        )
        self.device = self.registry.get_device(registered.id)
        self.original = self.registry.get_device(registered.id)
        # Simulate the monitor changing its previously loaded copy after a ping.
        self.device.current_state = DeviceState.DOWN
        self.device.last_check = datetime(2026, 10, 23, 12, 0)
        self.device.last_latency_ms = None
        self.device.consecutive_failures = 3
        self.device.consecutive_successes = 0

    def test_registry_metadata_edits_survive_repeated_status_writes(self):
        fields = dict(name="Office Router", hostname="office", device_type="switch", location="Office")
        self.registry.update_device(self.device.id, **fields)
        # Covers repeated check and shutdown saves using the stale monitor copy.
        for _ in range(2):
            self.assertTrue(self.store.update_device_status(self.device))
            saved = self.registry.get_device(self.device.id)
            for key, value in fields.items():
                self.assertEqual(getattr(saved, key), value)
            self.assertEqual(saved.ip_address, self.original.ip_address)
            self.assertEqual(saved.created_at, self.original.created_at)
            self.assertTrue(saved.is_active)
            self.assertEqual(saved.current_state, DeviceState.DOWN)

    def test_status_and_counters_are_saved_without_changing_other_devices(self):
        other = self.registry.add_device(name="Other", ip_address="192.0.2.2")
        other_before = self.registry.get_device(other.id)
        self.assertTrue(self.store.update_device_status(self.device))
        saved = self.registry.get_device(self.device.id)
        self.assertEqual(saved.last_check, self.device.last_check)
        self.assertIsNone(saved.last_latency_ms)
        self.assertEqual(saved.consecutive_failures, 3)
        self.assertEqual(saved.consecutive_successes, 0)
        self.device.current_state = DeviceState.UP
        self.device.last_latency_ms = 12.5
        self.device.consecutive_failures = 0
        self.device.consecutive_successes = 2
        self.assertTrue(self.store.update_device_status(self.device))
        saved = self.registry.get_device(self.device.id)
        self.assertEqual(saved.current_state, DeviceState.UP)
        self.assertEqual(saved.last_latency_ms, 12.5)
        self.assertEqual(saved.consecutive_failures, 0)
        self.assertEqual(saved.consecutive_successes, 2)
        self.assertEqual(self.registry.get_device(other.id), other_before)

    def test_changed_ip_rejects_stale_status_until_device_is_reloaded(self):
        self.registry.update_device(self.device.id, ip_address="192.0.2.9")
        before = self.registry.get_device(self.device.id)
        self.assertFalse(self.store.update_device_status(self.device))
        self.assertEqual(self.registry.get_device(self.device.id), before)
        reloaded = self.registry.get_device(self.device.id)
        reloaded.current_state = DeviceState.UP
        self.assertTrue(self.store.update_device_status(reloaded))
        self.assertEqual(self.registry.get_device(self.device.id).ip_address, "192.0.2.9")

    def test_deactivated_device_is_not_reactivated_or_updated(self):
        self.registry.deactivate_device(self.device.id)
        before = self.registry.get_device(self.device.id)
        self.assertFalse(self.store.update_device_status(self.device))
        self.assertEqual(self.registry.get_device(self.device.id), before)

    def test_deleted_device_is_not_recreated_by_repeated_saves(self):
        self.registry.delete_device(self.device.id)
        for _ in range(2):
            self.assertFalse(self.store.update_device_status(self.device))
            self.assertIsNone(self.registry.get_device(self.device.id))

    def test_unregistered_device_is_not_inserted(self):
        unknown = Device(name="Unregistered", ip_address="192.0.2.99")
        self.assertFalse(self.store.update_device_status(unknown))
        self.assertIsNone(self.registry.get_device(unknown.id))


if __name__ == "__main__":
    unittest.main()

# WatchTower Device Management CLI (Phase 4)

import sys
import argparse

sys.path.insert(0, ".")

from watchtower.storage.device_registry import DeviceRegistry


def print_device_row(d):
    state = d.current_state.value if hasattr(d.current_state, "value") else d.current_state
    status = "active" if d.is_active else "INACTIVE"
    print(f"  {d.id:10s} | {d.name:20s} | {d.ip_address:15s} | {d.device_type:10s} | {state:10s} | {status}")


def cmd_add(args, registry):
    try:
        device = registry.add_device(
            name=args.name,
            ip_address=args.ip,
            hostname=args.hostname or "",
            device_type=args.type,
            location=args.location or "",
        )
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    print(f"✅ Added device '{device.name}' (id: {device.id}, ip: {device.ip_address})")


def cmd_list(args, registry):
    devices = registry.list_devices(active_only=not args.all)
    if not devices:
        print("No devices found." + (" (try --all to include inactive)" if not args.all else ""))
        return
    print(f"{'ID':10s} | {'Name':20s} | {'IP Address':15s} | {'Type':10s} | {'State':10s} | Status")
    print("-" * 90)
    for d in devices:
        print_device_row(d)


def cmd_show(args, registry):
    d = registry.get_device(args.device_id)
    if not d:
        print(f"❌ No device found with id '{args.device_id}'")
        sys.exit(1)
    print(f"ID:              {d.id}")
    print(f"Name:            {d.name}")
    print(f"IP Address:      {d.ip_address}")
    print(f"Hostname:        {d.hostname}")
    print(f"Type:            {d.device_type}")
    print(f"Location:        {d.location}")
    print(f"Active:          {d.is_active}")
    print(f"Current State:   {d.current_state.value}")
    print(f"Last Check:      {d.last_check}")
    print(f"Last Latency:    {d.last_latency_ms} ms")


def cmd_update(args, registry):
    fields = {}
    if args.name:
        fields["name"] = args.name
    if args.ip:
        fields["ip_address"] = args.ip
    if args.hostname:
        fields["hostname"] = args.hostname
    if args.type:
        fields["device_type"] = args.type
    if args.location:
        fields["location"] = args.location

    if not fields:
        print("❌ Provide at least one field to update (--name, --ip, --hostname, --type, --location)")
        sys.exit(1)

    updated = registry.update_device(args.device_id, **fields)
    if not updated:
        print(f"❌ No device found with id '{args.device_id}'")
        sys.exit(1)
    print(f"✅ Updated device '{updated.name}' (id: {updated.id})")


def cmd_deactivate(args, registry):
    if registry.deactivate_device(args.device_id):
        print(f"✅ Deactivated device '{args.device_id}' — it will stop being monitored. History is preserved.")
    else:
        print(f"❌ No device found with id '{args.device_id}'")
        sys.exit(1)


def cmd_reactivate(args, registry):
    if registry.reactivate_device(args.device_id):
        print(f"✅ Reactivated device '{args.device_id}'")
    else:
        print(f"❌ No device found with id '{args.device_id}'")
        sys.exit(1)


def cmd_delete(args, registry):
    if not args.yes:
        confirm = input(f"Permanently delete device '{args.device_id}'? This cannot be undone. [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return
    if registry.delete_device(args.device_id):
        print(f"✅ Deleted device '{args.device_id}'")
    else:
        print(f"❌ No device found with id '{args.device_id}'")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="WatchTower device management CLI")
    parser.add_argument("--db", default="data/watchtower.db", help="Path to the SQLite database (default: data/watchtower.db)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add a new device")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--ip", required=True)
    p_add.add_argument("--hostname", default="")
    p_add.add_argument("--type", default="server")
    p_add.add_argument("--location", default="")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List devices")
    p_list.add_argument("--all", action="store_true", help="Include inactive devices")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show full details for one device")
    p_show.add_argument("device_id")
    p_show.set_defaults(func=cmd_show)

    p_update = sub.add_parser("update", help="Update one or more fields on a device")
    p_update.add_argument("device_id")
    p_update.add_argument("--name")
    p_update.add_argument("--ip")
    p_update.add_argument("--hostname")
    p_update.add_argument("--type")
    p_update.add_argument("--location")
    p_update.set_defaults(func=cmd_update)

    p_deact = sub.add_parser("deactivate", help="Stop monitoring a device, keep its history (soft delete)")
    p_deact.add_argument("device_id")
    p_deact.set_defaults(func=cmd_deactivate)

    p_react = sub.add_parser("reactivate", help="Resume monitoring a previously deactivated device")
    p_react.add_argument("device_id")
    p_react.set_defaults(func=cmd_reactivate)

    p_delete = sub.add_parser("delete", help="Permanently remove a device row")
    p_delete.add_argument("device_id")
    p_delete.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    p_delete.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    registry = DeviceRegistry(db_path=args.db)
    args.func(args, registry)


if __name__ == "__main__":
    main()

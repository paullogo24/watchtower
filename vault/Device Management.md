---
tags: [watchtower, commands]
updated: 2026-10-23
---

# Device Management

## Add devices

1. Stop `run.py` with **Ctrl+C** if it is running; wait for shutdown.
2. Open the project directory:

   ```bash
   cd /home/plogodzo/WT
   ```

3. Register a device, replacing the example address with its actual IP:

   ```bash
   python manage.py add --name "Main Router" --ip 192.168.1.1 --type router --location "Server Room"
   ```

   Only `--name` and `--ip` are required. `--type` defaults to `server`.
   `--hostname` and `--location` are optional.

   ```bash
   python manage.py add --name "Lab PC" --ip 192.168.1.20
   python manage.py add --name "Lab Switch" --ip 192.168.1.10 --type switch --hostname lab-switch
   ```

4. Verify registration, then start monitoring:

   ```bash
   python manage.py list --all
   python run.py
   ```

New devices are active and initially UNKNOWN. The runner loads active devices at
startup and currently runs for 180 seconds. Registrations persist between runs.

## Other commands

Replace `DEVICE_ID` with the ID printed by `add` or `list`.

```bash
python manage.py list
python manage.py list --all
python manage.py show DEVICE_ID
python manage.py update DEVICE_ID --location "Rack 3" --hostname router-main
python manage.py deactivate DEVICE_ID
python manage.py reactivate DEVICE_ID
```

Stop monitoring before making changes, then restart it. The engine does not
refresh registry changes while running. Registry edits are now protected from
status writes, but the engine can keep checking the previous IP and using old
alert labels until restarted. It can also keep recording events for a device
removed or deactivated during a run. See [[2026-10-23 Device Edit Protection]].

Deactivation preserves the device and its history. Permanent deletion removes
the registration and leaves history without its original device row:

```bash
python manage.py delete DEVICE_ID
```

The deletion command asks for confirmation. Its `--yes` option skips that prompt.

For another database, `--db` goes before the subcommand:

```bash
python manage.py --db /path/to/watchtower.db list --all
```

`run.py` still uses its hardcoded `data/watchtower.db` path; it will not
automatically monitor a database selected only through the CLI's `--db` option.

Related: [[History Cleanup]], [[Database]], [[Known Issues]].

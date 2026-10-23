---
tags: [watchtower, commands, database]
updated: 2026-10-23
---

# History Cleanup

## Clear scan history, keep devices

1. Stop `run.py` with **Ctrl+C** and wait for it to finish.
2. Run:

   ```bash
   cd /home/plogodzo/WT
   python manage.py clear-history
   ```

3. Enter `y` to confirm. An empty answer or anything other than `y` cancels.
4. Verify devices and restart monitoring:

   ```bash
   python manage.py list --all
   python run.py
   ```

## Effects

| Data | Result |
|---|---|
| All ping checks | Deleted |
| All state changes | Deleted |
| All alert records | Deleted |
| Device registration fields and IDs | Preserved |
| Active/inactive flags and creation dates | Preserved |
| Current state | Reset to UNKNOWN |
| Last check and latency | Cleared |
| Success/failure counters | Reset to zero |

Deletion and status reset commit in one transaction. A failure rolls back the
operation. The CLI prints deleted record counts.

Skip confirmation only when intentional:

```bash
python manage.py clear-history --yes
```

Choose a different database:

```bash
python manage.py --db /path/to/watchtower.db clear-history
```

> [!important] Stop the monitor first
> The command prints a reminder but does not automatically stop or lock out the
> monitor. A running monitor can add records and restore its in-memory status.

## What this does not do

It does not split the database or protect devices from deleting the database file.
It does not create a backup or clear only one device's history.

## Scheduled retention

`run.py` schedules event cleanup daily at 02:00 using `storage.retention_days`.
The fallback is 30 days. The job deletes old events, not device registrations.
It runs only while the process is active; missed runs are not caught up.

Source: `manage.py`, `watchtower/storage/sqlite_event_store.py`.
Tests: `tests/test_clear_history.py`.

Related: [[Database]], [[Development and Testing]], [[Configuration]].

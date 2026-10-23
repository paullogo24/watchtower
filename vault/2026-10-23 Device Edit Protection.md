---
tags: [watchtower, progress, database]
date: 2026-10-23
---

# 2026-10-23 Device Edit Protection

## Problem

The monitor kept a device snapshot in memory. Its database upsert rewrote both
metadata and status after checks and during shutdown. Renaming Main Router to
Office Router through the CLI could be undone by the next check. A deleted
registration could also be recreated.

## Change

Replaced `upsert_device()` with `update_device_status()` in
`watchtower/storage/sqlite_event_store.py` and switched the runner's check and
shutdown saves to the new method. Removed the unnecessary startup write.

The new method updates only current state, last-check time, latency, and
consecutive failure/success counters. Registry metadata is never written.
It performs a single conditional UPDATE against the device ID, original IP, and
active flag, returning false if no eligible row exists. It never inserts rows.

## Verification

Six new tests exercise stale monitor copies against independent registry updates
in temporary SQLite databases. Together with the five cleanup tests, all eleven
pass using:

```bash
python -B -m unittest discover -s tests -v
```

No live monitoring, SMTP delivery, or production database changes were needed.

## Remaining limitation

This protects stored device registrations. It does not refresh the engine's
in-memory devices. Restart monitoring to pick up new addresses, labels,
deactivation, or deletion. Until then, old targets can still be checked and
historical events recorded. See [[Known Issues]] and [[Roadmap]].

The vault now lives at `/home/plogodzo/WT/vault`; README and Home links reflect it.

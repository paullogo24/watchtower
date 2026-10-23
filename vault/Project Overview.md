---
tags: [watchtower, overview]
updated: 2026-10-23
---

# Project Overview

WatchTower monitors registered network devices using ICMP ping. It records
reachability and latency, tracks changes in device health, and groups changes
into email notifications.

## Implemented

- Device registration and management through `manage.py`.
- Scheduled ping checks with retries.
- UP, DOWN, DEGRADED, and UNKNOWN states.
- Consecutive failure and recovery thresholds.
- Batched SMTP alerts and duplicate suppression.
- SQLite event history and Python reporting queries.
- Daily retention cleanup while the runner is active.
- Manual history cleanup that preserves device registrations.

Device discovery is manual: registering an IP is not automatic subnet discovery.
The implemented checks measure availability and latency, not intrusion detection.

## Stack

| Component | Implementation |
|---|---|
| Language | Python |
| Network checks | ping3 |
| Scheduling | schedule plus a background thread |
| Database | SQLite through SQLAlchemy |
| Configuration | PyYAML |
| Notifications | SMTP through Python's standard library |
| Planned web interface | Flask; listed as a dependency, not implemented |

The current `run.py` is a 180-second demonstration runner. It is not yet a
continuously running monitoring service.

See [[Architecture]], [[Known Issues]], and [[Roadmap]].

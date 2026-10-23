---
tags: [watchtower, database]
updated: 2026-10-23
---

# Database

## Current design

All device registrations and monitoring history live in `data/watchtower.db`.
SQLAlchemy models are in `watchtower/models_sql.py`; engine/session setup is in
`watchtower/database.py`.

| Table | Contents |
|---|---|
| `devices` | ID, name, IP, hostname, type, location, active flag, creation time, current state, latest check/latency, counters |
| `checks` | Check outcome, device ID, timestamp, latency, retry attempt, error |
| `state_changes` | Device ID, old/new state, timestamp, reason, latency |
| `alerts` | Alert type, severity, delivery outcome, message, error, device/batch identifier |

Device IDs are separate from IP addresses. This allows identity and history to
survive address changes. IDs currently use eight characters from a generated UUID.

Event device IDs are indexed, but the models do not define foreign keys.
Batch alert records use `batch` as their device identifier, so a future relationship
design must account for alerts involving multiple devices.

## What we decided

- Keep SQLite for the current local application.
- Preserve registrations when manually clearing history.
- Reset stored monitoring status when clearing history.
- Prefer deactivation when device history must remain meaningful.
- Registry operations own device creation and metadata edits.
- Monitoring uses `update_device_status()` to save state, last-check time, latency,
  and success/failure counters only. It does not insert device rows.
- Status writes require an existing active registration with the same IP as the
  monitor's copy. This check and update happen in one SQL statement.

## Discussed, not implemented

We considered separating registrations into `registry/devices.db` and keeping
history in `data/watchtower.db`. This split has **not** been implemented.
The `clear-history` command achieves selective cleanup inside the existing file.

Deleting the SQLite file still deletes devices too. See [[History Cleanup]].

## Improvements to make

- Enforce the intended uniqueness rule for active IP addresses in the database.
- Validate and normalize IP addresses on add and update.
- Define deletion/history relationships explicitly.
- Use full UUIDs internally.
- Add schema migrations and a backup/restore procedure before structural changes.

## Reporting caveat

`Queries.device_uptime()` calculates successful checks divided by total checks.
It is a sample success percentage, not time-weighted uptime, and currently returns
100% when no data exists. A future report should distinguish “no data.”

Related: [[Known Issues]], [[Roadmap]], [[Device Management]].

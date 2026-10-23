---
tags: [watchtower, issues]
updated: 2026-10-23
---

# Known Issues

These findings come from source review. History cleanup and device-status
persistence have automated tests; no live network or SMTP session was used.

## Resolved: device edits overwritten by monitoring

Replaced the broad upsert with `SQLiteEventStore.update_device_status()`.
Monitoring now updates only state, last-check time, latency, and counters.
Deleted, inactive, or readdressed registrations are skipped. Six regression tests
cover this behavior; see [[2026-10-23 Device Edit Protection]].

## Registry changes require restart

Active devices are loaded only at startup. Deactivating a device in SQLite does
not update the monitor's in-memory copy immediately. Protection of device rows
does not stop checks or historical-event writes against stale targets.

**Current procedure:** stop monitoring, edit devices, restart.

## Duplicate and invalid addresses

Duplicate active IPs are checked during addition, but not during updates or
reactivation. The schema lacks an enforcing uniqueness constraint and the CLI
does not validate IP syntax.

## Incomplete persistence and relationships

Success/failure counters are now saved by monitoring and loaded by the registry.
Permanent device deletion still leaves orphaned history. Device IDs use only
eight UUID characters.

## Alert timing can drift indefinitely

Every qualifying state change cancels and restarts the batch timer. Continuous
changes can postpone delivery. Use a fixed window beginning with the first
pending change and test behavior under repeated events.

The email status list is populated from devices seen by the notifier through
state changes, so it is not guaranteed to include every registered device.

## State-transition edge cases

- Recovery from DOWN sets UP after enough successes even if latency is high.
- Successful high-latency pings increment the same success counter as healthy
  pings, so recovery from DEGRADED may require fewer healthy checks than intended.

Add focused state-machine tests and define the expected recovery behavior.

## Reporting and operation

- “Uptime” is check success percentage; no samples currently yields 100%.
- The runner exits after 180 seconds and ignores YAML monitoring values.
- Checks run sequentially, so slow devices delay other checks.
- Daily retention depends on the process being alive at the scheduled time.
- Schema migrations, automated backups, dashboard, and service setup are pending.

Related: [[Roadmap]], [[Database]], [[Configuration]].

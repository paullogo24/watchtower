---
tags: [watchtower, planning]
updated: 2026-10-23
---

# Roadmap

## Already present before the review

- [x] Ping monitoring with retries and device-state transitions.
- [x] Batched email alerts and duplicate suppression.
- [x] SQLite event storage and historical reporting helpers.
- [x] CLI device registration, editing, deactivation, reactivation, deletion.
- [x] Scheduled retention cleanup.

## Completed during this work

- [x] Review architecture and database/device persistence.
- [x] Implement `clear-history` with confirmation and `--yes`.
- [x] Preserve registrations while resetting monitoring status.
- [x] Make cleanup atomic and return deletion counts.
- [x] Add five cleanup regression tests; all passed.
- [x] Document adding devices and clearing history in README.
- [x] Create this linked Obsidian reference vault.
- [x] Protect registry edits with status-only monitoring writes.
- [x] Add six device-status regression tests; all eleven tests pass.

## Next: protect device data

- [x] Separate status updates from registry metadata updates.
- [x] Prevent the monitor from recreating deleted registrations.
- [x] Skip status updates for inactive devices and changed IP addresses.
- [x] Persist success/failure counters during status updates.
- [ ] Define registry refresh behavior during monitoring.
- [ ] Validate addresses and enforce active-IP uniqueness on all write paths.
- [ ] Resolve device/history deletion policy.

## Then: dependable operation

- [ ] Add continuous operation with orderly shutdown.
- [ ] Load and validate monitoring settings from YAML.
- [ ] Fix batch timing and full-device email status coverage.
- [ ] Test state transitions, registry updates, and alert scheduling.
- [ ] Represent missing uptime data clearly.
- [ ] Add schema migrations and backup/restore instructions.

## Later features

- [ ] Dashboard and REST API.
- [ ] Packaging and systemd service setup.
- [ ] Consider parallel checks if measurements show scheduling delays.

## Decision still open

- [ ] Decide whether device registration needs a separate database file.

The separate-registry proposal is optional and unimplemented. `clear-history`
already preserves devices when used instead of deleting the database file.

Related: [[Known Issues]], [[2026-10-23 Project Progress]].

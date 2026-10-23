---
tags: [watchtower, configuration]
updated: 2026-10-23
---

# Configuration

`watchtower/config.py` loads `config.yaml` and merges it with defaults.
This vault does not copy local credentials or device inventory.

## Effective runner settings

These values are hardcoded in `run.py`, rather than read from the YAML monitoring
section:

| Setting | Current value |
|---|---|
| Ping interval | 30 seconds |
| Timeout per attempt | 2 seconds |
| Attempts per check | 3 |
| High-latency threshold | 50 ms |
| Failures before DOWN | 3 failed checks |
| Successes before recovery from DOWN | 2 successful checks |
| Run duration | 180 seconds |
| Batch delay | 60 seconds, restarted on qualifying changes |
| Database | `data/watchtower.db` |

Three attempts happen within one check. Three failed checks are therefore
different from three failed ping attempts. Actual timing includes retries and
sequential scheduling delays.

## Settings read from configuration

- `alerts.email`: enable flag, SMTP connection, credentials, sender, recipients, TLS.
- `alerts.deduplication_window_sec`: defaults to 300 seconds.
- `storage.retention_days`: defaults to 30 days if absent.

The configured storage directory is not currently wired into the runner's
database path. Dashboard settings exist, but a dashboard does not yet exist.

## Planned improvement

Build `MonitoringConfig` from validated YAML values and expose an explicit
continuous mode or run duration. Keep examples and defaults consistent with the
actual runner.

Source: `run.py`, `watchtower/config.py`, `watchtower/models.py`.

Related: [[Architecture]], [[Known Issues]], [[Roadmap]].

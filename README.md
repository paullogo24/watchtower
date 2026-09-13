# 🗼 WatchTower

**Infrastructure monitoring and network security project**

A lightweight, Python-based system that monitors network devices, detects outages, tracks latency, and sends batched email alerts — built for small-scale environments like university labs, regional telecom setups, and small IT teams.

---

## ✨ Features

| Feature | Status |
|---------|--------|
| **Host Discovery** | ✅Register devices by IP or hostname |
| **Network Scanning** | ✅Periodic ICMP ping checks with retry logic |
| **Infrastructure Monitoring** | ✅Tracks device health in real-time (UP/DOWN/DEGRADED) |
| **Alert System** | ✅ Batched email alerts — one email with all changes |
| **Event Logging** | ✅ Persisted to a queryable SQLite database |
| **Historical Reporting** | ✅ Uptime %, outage history, latency trends, summary reports |
| **State Machine** | Hysteresis prevents flapping (no false alarms) |
| **Deduplication** | Suppresses duplicate alerts within 5-minute window |

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Alerts

Edit `config.yaml`:

```yaml
alerts:
  email:
    enabled: true
    username: "your-email@gmail.com"
    password: "your-app-password"  # Gmail App Password, not your regular password
    from_address: "WatchTower <your-email@gmail.com>"
    to_addresses:
      - "admin@yourdomain.com"
    use_tls: true
```

**Get a Gmail App Password:**
1. Go to [myaccount.google.com](https://myaccount.google.com) → Security
2. Enable **2-Step Verification**
3. Security → **App passwords** → Select "Mail" + "Other (Custom name)"
4. Type "WatchTower" → Generate → Copy the 16-character password

> ⚠️ `config.yaml` contains live credentials and is gitignored. It is **not** tracked in this repo — create your own local copy before running.

### 3. Add Your Devices

Edit `run.py`, replace test devices with your real IPs:

```python
devices = [
    Device(
        name="Main Router",
        ip_address="192.168.1.1",
        hostname="router-main",
        device_type="router",
        location="Server Room"
    ),
]
```

### 4. Run

```bash
python run.py
```

This creates `data/watchtower.db` automatically on first run and starts writing every check, state change, and alert to it in real time.

---

## 📊 How It Works

### Monitoring Cycle
- Devices are pinged every `ping_interval_sec` (default 30s)
- Each check gets `retry_count` attempts (default 3) before being marked failed
- State changes trigger the alert system and are written to the database

### Alert Threshold (Hysteresis)
A device is only marked DOWN — and only then does an alert fire — after `consecutive_failures_before_alert` (default 3) consecutive failed checks. At a 30s interval, that's roughly 90 seconds of sustained downtime before anything is flagged. This avoids false alarms from a single dropped packet or brief network blip. Recovery works the same way in reverse: `consecutive_successes_before_recovery` (default 2) consecutive successful checks before a device is marked back UP.

### Batched Alerts
- State changes are collected over a `batch_window_sec` window (default 60s)
- One email is sent containing:
  - All devices that changed state (with old → new status)
  - A full status table of **all** monitored devices
- No more spam — one email per minute max, regardless of how many devices fail

### State Machine

| State | Emoji | Meaning | Trigger |
|-------|-------|---------|---------|
| **UP** | 🟢 | Responding normally | Consecutive successful pings |
| **DOWN** | 🔴 | Unreachable | Consecutive ping failures |
| **DEGRADED** | 🟡 | High latency | Latency exceeds threshold |
| **UNKNOWN** | ⚪ | Not yet checked | Initial state |

---

## 🗄️ Database (SQLite)

As of Phase 3, all monitoring data is persisted to `data/watchtower.db` via SQLAlchemy, replacing the earlier JSON-lines files.

**Tables:**

| Table | Purpose |
|-------|---------|
| `devices` | Current state of every monitored device (synced on every check) |
| `checks` | Every individual ping result (timestamp, success, latency, errors) |
| `state_changes` | Every UP/DOWN/DEGRADED transition |
| `alerts` | Every alert sent, suppressed, or failed |

**Inspect it directly:**

```bash
sqlite3 data/watchtower.db
.tables
.schema devices
SELECT * FROM checks ORDER BY timestamp DESC LIMIT 10;
```

**Or query it from Python** via `watchtower/storage/queries.py`:

```python
from watchtower.storage.queries import Queries

q = Queries("data/watchtower.db")
q.device_uptime(device_id, hours=24)      # uptime %
q.outage_history(hours=24)                # recent DOWN events
q.latency_trend(device_id, hours=24)      # for graphing
q.all_devices_status()                    # current status of every device
q.summary_report(hours=24)                # totals + success rate
```

**Retention:** old records can be purged with `store.delete_old_events(days=30)` (uses `storage.retention_days` from `config.yaml`). Not yet wired into a scheduled job — currently a manual/future call.

---

## 🏗️ Architecture

```
watchtower/
├── run.py                    ← Entry point (SQLite-backed)
├── run_phase3.py             ← Phase 3 SQLite demo/reference script
├── requirements.txt          ← Dependencies
├── config.yaml                ← Settings (gitignored, not tracked)
├── data/
│   └── watchtower.db         ← SQLite database (auto-created)
├── logs/                     ← Application logs
├── tests/                    ← Test suite
└── watchtower/                ← Core package
    ├── __init__.py
    ├── config.py              ← YAML config loader
    ├── models.py               ← Plain dataclasses: Device, CheckResult, StateChange, AlertLog
    ├── models_sql.py           ← SQLAlchemy ORM models: DeviceDB, CheckResultDB, StateChangeDB, AlertLogDB
    ├── database.py             ← SQLAlchemy engine/session setup
    ├── monitor/
    │   ├── engine.py           ← Core monitoring loop
    │   ├── ping_worker.py      ← ICMP ping with retries
    │   └── state_manager.py    ← State machine with hysteresis
    ├── storage/
    │   ├── event_store.py      ← Legacy JSON-lines store (kept for reference)
    │   ├── sqlite_event_store.py  ← Active SQLite-backed event store
    │   └── queries.py          ← Historical queries: uptime, outages, trends, reports
    ├── alerts/
    │   ├── deduplicator.py     ← Prevents alert spam
    │   ├── email_alert.py      ← SMTP email sender (individual)
    │   ├── batch_email_alert.py ← Batched email sender
    │   ├── notifier.py         ← Alert coordinator (individual)
    │   └── batch_notifier.py   ← Batched alert coordinator ← USE THIS
    ├── dashboard/               ← Web UI (Phase 5)
    └── utils/                   ← Helpers
```

---

## 🛠️ Tech Stack

| Layer | Tool |
|-------|------|
| Language | Python 3.11+ |
| Ping Engine | `ping3` |
| Scheduling | `schedule` |
| Config | `PyYAML` |
| Database | `SQLite` via `SQLAlchemy` ✅ |
| Web Framework | `Flask` *(Phase 5)* |

---

## ⚙️ Configuration

### `config.yaml` Reference

```yaml
monitoring:
  default_interval_sec: 30
  default_timeout_sec: 2.0
  default_retry_count: 3
  default_latency_threshold_ms: 100
  default_failures_before_alert: 3
  default_successes_before_recovery: 2

database:
  host: localhost
  port: 3306
  user: watchtower
  password: ""
  name: watchtower

alerts:
  deduplication_window_sec: 300  # 5 min — suppress duplicate alerts
  email:
    enabled: false               # Set to true to enable
    smtp_host: smtp.gmail.com
    smtp_port: 587
    username: ""
    password: ""
    from_address: ""
    to_addresses: []
    use_tls: true

dashboard:
  host: 0.0.0.0
  port: 5000
  debug: false

storage:
  data_dir: "data"
  retention_days: 30
```

---

## 📅 Build Roadmap

| Phase | Component | Status |
|-------|-----------|--------|
| **1** | Monitor Engine (ping + state machine) | ✅ Done |
| **2** | Alert System (batched email) | ✅ Done |
| **3** | Event Logger (SQLite migration) | ✅ Done |
| **4** | Device Registry (CRUD + web management) | ⏳ Pending |
| **5** | Dashboard (Flask UI + REST API) | ⏳ Pending |
| **6** | CLI + Packaging + Systemd | ⏳ Pending |

---

## 🔒 Security Notes

- `config.yaml` holds live SMTP and database credentials and is **gitignored** — never commit it.
- Gmail alerts use an **App Password**, not the account password.
- Git history has been purged (`git filter-repo`) of an earlier accidental credential leak; the exposed app password has been revoked and rotated.

---

## 🤝 Contributing

Built by **paulogo24** as a cybersecurity project for infrastructure monitoring and network security.

---

## 📜 License

MIT License
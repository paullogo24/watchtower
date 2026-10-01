# 🗼 WatchTower

**Infrastructure monitoring and network security project**

A lightweight, Python-based system that monitors network devices, detects outages, tracks latency, and sends batched email alerts — built for small-scale environments like university labs, regional telecom setups, and small IT teams.

---

## ✨ Features

| Feature | Status |
|---------|--------|
| **Host Discovery** | ✅ Devices registered via CLI, stored in SQLite |
| **Network Scanning** | ✅ Periodic ICMP ping checks with retry logic |
| **Infrastructure Monitoring** | ✅ Real-time device health tracking (UP/DOWN/DEGRADED) |
| **Alert System** | ✅ Batched email alerts — one email with all changes |
| **Event Logging** | ✅ Persisted to a queryable SQLite database |
| **Historical Reporting** | ✅ Uptime %, outage history, latency trends |
| **Device Management** | ✅ Add/update/deactivate/delete devices via CLI — no code edits needed |
| **Data Retention** | ✅ Auto-purges records older than 30 days (daily job) |
| **State Machine** | ✅ Hysteresis prevents flapping (no false alarms) |
| **Deduplication** | ✅ Suppresses duplicate alerts within a 5-minute window |

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Alerts

Create your own local `config.yaml` (it's gitignored and not tracked in this repo):

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

### 3. Add Your Devices

Devices are no longer hardcoded — they're managed through `manage.py`, which stores them in the SQLite database:

```bash
python manage.py add --name "Main Router" --ip 192.168.1.1 --type router --location "Server Room"
python manage.py add --name "Lab Switch" --ip 192.168.1.10 --type switch
python manage.py list
```

### 4. Run

```bash
python run.py
```

On first run, this creates `data/watchtower.db` if it doesn't already exist, loads every active device from the registry, and starts monitoring.

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
- One email is sent containing all devices that changed state plus a full status table of every monitored device
- No more spam — one email per minute max, regardless of how many devices fail

### State Machine

| State | Emoji | Meaning | Trigger |
|-------|-------|---------|---------|
| **UP** | 🟢 | Responding normally | Consecutive successful pings |
| **DOWN** | 🔴 | Unreachable | Consecutive ping failures |
| **DEGRADED** | 🟡 | High latency | Latency exceeds threshold |
| **UNKNOWN** | ⚪ | Not yet checked | Initial state |

---

## 🧰 Managing Devices (`manage.py`)

Devices live in the `devices` table of `data/watchtower.db` and are managed entirely through the CLI — no code edits required.

```bash
# Add a device
python manage.py add --name "Main Router" --ip 192.168.1.1 --type router --location "Server Room"

# List devices
python manage.py list              # active only
python manage.py list --all        # include deactivated

# View full details
python manage.py show <device_id>

# Update a field
python manage.py update <device_id> --location "Rack 3" --hostname router-main

# Stop monitoring a device but keep its history (soft delete)
python manage.py deactivate <device_id>
python manage.py reactivate <device_id>

# Permanently remove a device row
python manage.py delete <device_id> [--yes]
```

Duplicate active IPs are rejected automatically. `run.py` loads whatever is currently active in the registry at startup — if none are registered, it prints a reminder to add one instead of crashing.

---

## 🗄️ Database (SQLite)

All monitoring data is persisted to `data/watchtower.db` via SQLAlchemy.

**Tables:**

| Table | Purpose |
|-------|---------|
| `devices` | Registered devices + their current live state (synced every check) |
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
q.device_uptime(device_id, hours=24)
q.outage_history(hours=24)
q.latency_trend(device_id, hours=24)
q.all_devices_status()
q.summary_report(hours=24)
```

### Retention

A daily job (scheduled for 02:00, riding on the same background scheduler used for ping checks) automatically purges `checks`, `state_changes`, and `alerts` older than `storage.retention_days` (default 30) from `config.yaml`. `devices` rows are never auto-deleted.

> **Note:** this only runs while `run.py` is actively running at 02:00. If the process isn't alive at that moment, that day's cleanup is simply skipped — it is not "caught up" later, though the 30-day cutoff itself is always calculated relative to the moment cleanup actually runs, so nothing is lost or double-counted.

**If you ever delete `data/watchtower.db`,** everything in it — devices, check history, state changes, alerts — is gone permanently, with no automatic backup. Copy the file manually (`cp data/watchtower.db data/watchtower.db.backup`) before doing anything risky.

---

## 🏗️ Architecture

```
watchtower/
├── run.py                    ← Entry point (loads devices from DB)
├── manage.py                 ← Device management CLI
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
    │   ├── device_registry.py  ← CRUD layer for the devices table
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
    enabled: false
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
| **4** | Device Registry (CRUD CLI + database) | ✅ Done |
| **5** | Dashboard (Flask UI + REST API) | ⏳ Pending |
| **6** | CLI + Packaging + Systemd | ⏳ Pending |

---

## 🔒 Security Notes

- `config.yaml` holds live SMTP and database credentials and is **gitignored** — never commit it.
- Gmail alerts use an **App Password**, not the account password.
- Git history has previously been purged (`git filter-repo`) of an accidental credential leak; the exposed app password was revoked and rotated.

---

## 🤝 Contributing

Built by **paulogo24** as a cybersecurity project for infrastructure monitoring and network security.

---

## 📜 License

MIT License
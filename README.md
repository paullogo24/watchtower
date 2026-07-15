# 🗼 WatchTower

**Infrastructure monitoring and network security project**

A lightweight, Python-based system that monitors network devices, detects outages, tracks latency, and sends batched email alerts — built for small-scale environments like university labs, regional telecom setups, and small IT teams.

---

## ✨ Features

| Feature | Status |
|---------|--------|
| **Host Discovery** | Register devices by IP or hostname |
| **Network Scanning** | Periodic ICMP ping checks with retry logic |
| **Infrastructure Monitoring** | Tracks device health in real-time (UP/DOWN/DEGRADED) |
| **Alert System** | ✅ Batched email alerts — one email with all changes |
| **Event Logging** | Persists all checks and state changes for analysis |
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
    from_address: "watchtower@yourdomain.com"
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

---

## 📊 How It Works

### Monitoring Cycle
- Devices are pinged every X seconds (configurable, default 30s)
- Each device gets `retry_count` attempts before marked failed
- State changes trigger the alert system

### Batched Alerts
- State changes are collected over a `batch_window_sec` window (default 60s)
- One email is sent containing:
  - All devices that changed state (with old → new status)
  - A full status table of **all** monitored devices
- No more spam — one email per minute max, regardless of how many devices fail

### State Machine

| State | Emoji | Meaning | Trigger |
|-------|-------|---------|---------|
| **UP** | 🟢 | Responding normally | 2+ consecutive successful pings |
| **DOWN** | 🔴 | Unreachable | 2+ consecutive ping failures |
| **DEGRADED** | 🟡 | High latency | Latency exceeds threshold |
| **UNKNOWN** | ⚪ | Not yet checked | Initial state |

**Hysteresis:** Device needs 2 consecutive failures before marked DOWN, and 2 consecutive successes before recovering. Prevents flapping from single packet loss.

---

## 🏗️ Architecture

```
watchtower/
├── run.py                    ← Entry point / demo
├── requirements.txt          ← Dependencies
├── config.yaml               ← Settings (email, intervals, thresholds)
├── data/                     ← Event logs (auto-created)
│   ├── checks.jsonl
│   ├── state_changes.jsonl
│   └── alerts.jsonl
├── logs/                     ← Application logs
├── tests/                    ← Test suite
└── watchtower/               ← Core package
    ├── __init__.py
    ├── config.py             ← YAML config loader
    ├── models.py             ← Data structures
    ├── monitor/
    │   ├── engine.py         ← Core monitoring loop
    │   ├── ping_worker.py    ← ICMP ping with retries
    │   └── state_manager.py  ← State machine with hysteresis
    ├── storage/
    │   └── event_store.py    ← JSON-lines persistence
    ├── alerts/
    │   ├── deduplicator.py   ← Prevents alert spam
    │   ├── email_alert.py    ← SMTP email sender (individual)
    │   ├── batch_email_alert.py  ← Batched email sender
    │   ├── notifier.py       ← Alert coordinator (individual)
    │   └── batch_notifier.py ← Batched alert coordinator ← USE THIS
    ├── dashboard/            ← Web UI (Phase 5)
    └── utils/                ← Helpers
```

---

## 🛠️ Tech Stack

| Layer | Tool |
|-------|------|
| Language | Python 3.11+ |
| Ping Engine | `ping3` |
| Scheduling | `schedule` |
| Config | `PyYAML` |
| Web Framework | `Flask` *(Phase 5)* |
| Database | `SQLite` *(Phase 4)* |

---

## ⚙️ Configuration

### `config.yaml` Reference

```yaml
monitoring:
  default_interval_sec: 30      # How often to ping each device
  default_timeout_sec: 2.0      # Ping timeout
  default_retry_count: 3        # Retries before marking failed
  default_latency_threshold_ms: 100  # DEGRADED trigger
  default_failures_before_alert: 2   # DOWN trigger
  default_successes_before_recovery: 2  # UP recovery

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
| **3** | Event Logger (SQLite migration) | ⏳ Pending |
| **4** | Device Registry (CRUD + database) | ⏳ Pending |
| **5** | Dashboard (Flask UI + REST API) | ⏳ Pending |
| **6** | CLI + Packaging + Systemd | ⏳ Pending |

---

## 🤝 Contributing

Built by **paulogo24** as a cybersecurity project for infrastructure monitoring and network security.

---

## 📜 License

MIT License

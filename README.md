🗼 WatchTower

Infrastructure monitoring and network security project

A lightweight, Python-based system that monitors network devices, detects outages, and tracks latency — built for small-scale environments like university labs, regional telecom setups, and small IT teams.

✨ What It Does

    • Host Discovery — Register devices by IP or hostname
    
    • Network Scanning — Periodic ICMP ping checks with retry logic
    
    • Infrastructure Monitoring — Tracks device health in real-time
    
    • Alert System (Phase 2 — coming soon) — Email notifications on outages
    
    • Event Logging — Persists all checks and state changes for analysis
    

🏗️ Architecture

    watchtower/

    ├── run.py                    ← Demo entry point

    ├── requirements.txt          ← Python dependencies

    ├── config.yaml               ← Configuration template

    ├── data/                     ← Event logs (JSON lines)

    ├── logs/                     ← Application logs

    ├── tests/                    ← Test suite (future)

    └── watchtower/               ← Core package

    ├── models.py             ← Data structures (Device, CheckResult, etc.)
    
    ├── monitor/
    
    │   ├── engine.py         ← Core monitoring loop & scheduler
    
    │   ├── ping_worker.py    ← ICMP ping with retries
    
    │   └── state_manager.py  ← State machine with hysteresis
    
    ├── storage/
    
    │   └── event_store.py    ← JSON-lines persistence
    
    ├── alerts/               ← Alert system (Phase 2)
    
    ├── dashboard/            ← Web UI (Phase 5)
    
    └── utils/                ← Helpers (future)
    
    

🚀 Quick Start

1. Install Dependencies
   
pip install -r requirements.txt

3. Run the Monitor Engine Demo
   
python run.py

This starts a 60-second demo that monitors: - 127.0.0.1 (localhost — always up) - 8.8.8.8 (Google DNS — internet test) - 192.0.2.1 (fake device — guaranteed down, for testing alerts)

5. Add Your Own Devices
   
Edit run.py and replace the test devices with your real IPs:

     devices = [

    Device(
        name="Main Router",
        ip_address="192.168.1.1",
        hostname="router-main",
        device_type="router",
        location="Server Room"
    ),
]

📊 State Machine

Devices are tracked in 4 states with hysteresis to prevent flapping:

State	Emoji	Meaning

UP	🟢	Responding normally

DOWN	🔴	Unreachable after retries

DEGRADED	🟡	Responding but high latency

UNKNOWN	⚪	Not yet checked

Hysteresis rules: - Device needs 2 consecutive failures before marked DOWN - Device needs 2 consecutive successes before recovering from DOWN - Latency above threshold triggers DEGRADED


🧪 Test Results

All core components tested and passing:

Test	Status

State Machine — UP → DOWN → UP	✅

DEGRADED detection (high latency)	✅

Event Store — JSON persistence	✅

Monitor Engine — Full integration	✅


🛠️ Tech Stack

Layer	Tool

Language	Python 3.11+

Ping Engine	ping3

Scheduling	schedule

Web Framework	Flask (Phase 5)

Database	SQLite (Phase 4)

ORM	SQLAlchemy (Phase 4)

Config	PyYAML


📅 Build Roadmap

Phase	Component	Status

1	Monitor Engine (ping loop + state machine)	✅ Done

2	Alert System (email notifications)	⏳ Next

3	Event Logger (SQLite + historical data)	⏳ Pending

4	Device Registry (CRUD + database)	⏳ Pending

5	Dashboard (Flask UI + REST API + real-time updates)	⏳ Pending

6	CLI + Config + Packaging	⏳ Pending


⚠️ Current Limitations

This is a skeleton / proof-of-concept. What’s working: - ✅ ICMP ping with retries - ✅ State machine with hysteresis - ✅ JSON-lines event logging - ✅ Background scheduler

What’s missing: - ❌ Persistent database (SQLite/PostgreSQL) - ❌ Email/SMS alerts - ❌ Web dashboard - ❌ Device management UI - ❌ Runs as a service (currently demo-only)


🤝 Contributing

Built by paullogo24 as a cybersecurity project for infrastructure monitoring and network security.

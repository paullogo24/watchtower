#loading settings from config.yaml
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    
    
    DEFAULTS = {
        "monitoring": {
            "default_interval_sec": 60,
            "default_timeout_sec": 2.0,
            "default_retry_count": 3,
            "default_latency_threshold_ms": 100,
            "default_failures_before_alert": 2,
            "default_successes_before_recovery": 2,
        },
        "alerts": {
            "email": {
                "enabled": False,
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_address": "watchtower@localhost",
                "to_addresses": [],
                "use_tls": True,
            },
            "deduplication_window_sec": 300,
        },
        "dashboard": {
            "host": "0.0.0.0",
            "port": 5000,
            "debug": False,
        },
        "storage": {
            "data_dir": "data",
            "retention_days": 30,
        }
    }
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config = self._load()
    
    def _load(self) -> Dict[str, Any]:
        config = dict(self.DEFAULTS)
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}
            self._deep_merge(config, user_config)
        return config
    
    def _deep_merge(self, base: Dict, override: Dict):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get(self, *keys: str, default: Any = None) -> Any:
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    @property
    def monitoring(self) -> Dict[str, Any]:
        return self._config["monitoring"]
    
    @property
    def alerts(self) -> Dict[str, Any]:
        return self._config["alerts"]
    
    @property
    def email(self) -> Dict[str, Any]:
        return self._config["alerts"]["email"]
    
    @property
    def dashboard(self) -> Dict[str, Any]:
        return self._config["dashboard"]
    
    @property
    def storage(self) -> Dict[str, Any]:
        return self._config["storage"]
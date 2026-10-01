"""
Ping Worker — Low-level ICMP ping using ping3 library.
Handles retries and returns structured CheckResult.
"""
import time
from typing import Optional
from ping3 import ping

from watchtower.models import CheckResult, Device


class PingWorker:
    """Executes ping checks against a single device with retry logic."""

    def __init__(self, timeout: float = 2.0, retry_count: int = 3):
        self.timeout = timeout
        self.retry_count = retry_count

    def check(self, device: Device) -> CheckResult:
        """
        Ping a device. Retry on failure up to retry_count times.
        Returns the best result (lowest latency if any success).
        """
        best_latency: Optional[float] = None
        last_error: Optional[str] = None

        for attempt in range(1, self.retry_count + 1):
            latency = ping(device.ip_address, timeout=self.timeout, unit='ms')

            if latency is not None and latency is not False:
                # Success — ping3 returns latency in ms
                if best_latency is None or latency < best_latency:
                    best_latency = latency
                # If we get a good ping, we don't need to retry
                if latency > 0:
                    return CheckResult(
                        device_id=device.id,
                        success=True,
                        latency_ms=round(latency, 2),
                        attempt_number=attempt
                    )
            else:
                last_error = f"No response within {self.timeout}s"
                time.sleep(0.5)  # Brief pause before retry

        # All retries have been used up
        return CheckResult(
            device_id=device.id,
            success=False,
            latency_ms=None,
            error_message=last_error or "Host unreachable",
            attempt_number=self.retry_count
        )

"""
Batch Email Alert — Sends a single email with all device status changes.
Collects state changes over a window and sends one consolidated alert.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional, Dict
from dataclasses import dataclass

from watchtower.models import Device, DeviceState, StateChange, AlertLog, AlertSeverity
from watchtower.config import Config


@dataclass
class BatchEntry:
    """A single state change entry for batching."""
    device: Device
    change: StateChange


class BatchEmailAlert:
    """Sends batched email alerts — one email with all device changes."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.email_cfg = self.config.email
        self.enabled = self.email_cfg.get("enabled", False)
        self.smtp_host = self.email_cfg.get("smtp_host", "smtp.gmail.com")
        self.smtp_port = self.email_cfg.get("smtp_port", 587)
        self.username = self.email_cfg.get("username", "")
        self.password = self.email_cfg.get("password", "")
        self.from_address = self.email_cfg.get("from_address", "watchtower@localhost")
        self.to_addresses = self.email_cfg.get("to_addresses", [])
        self.use_tls = self.email_cfg.get("use_tls", True)

        # Batch collection
        self._batch: List[BatchEntry] = []
        self._last_sent = datetime.min

    def add_to_batch(self, change: StateChange, device: Device):
        """Add a state change to the current batch."""
        self._batch.append(BatchEntry(device=device, change=change))

    def send_batch(self, all_devices: List[Device]) -> AlertLog:
        """
        Send a single email with all batched state changes.
        Includes a full status table of all monitored devices.
        """
        if not self._batch:
            return AlertLog(
                device_id="batch",
                alert_type="email",
                message="No changes to report",
                sent_successfully=True
            )

        if not self.enabled:
            self._batch.clear()
            return AlertLog(
                device_id="batch",
                alert_type="email",
                message="Email alerts disabled in config",
                sent_successfully=False
            )

        if not self.to_addresses:
            self._batch.clear()
            return AlertLog(
                device_id="batch",
                alert_type="email",
                message="No recipients configured",
                sent_successfully=False
            )

        # Determine overall severity
        severity = self._batch_severity()
        subject = self._build_subject()
        body_text = self._build_text_body(all_devices)
        body_html = self._build_html_body(all_devices)

        try:
            self._send_email(subject, body_text, body_html)
            count = len(self._batch)
            self._batch.clear()
            self._last_sent = datetime.utcnow()
            return AlertLog(
                device_id="batch",
                alert_type="email",
                severity=severity,
                message=f"Batch alert: {count} device(s) changed state",
                sent_successfully=True
            )
        except Exception as e:
            count = len(self._batch)
            self._batch.clear()
            return AlertLog(
                device_id="batch",
                alert_type="email",
                severity=severity,
                message=f"Batch alert: {count} device(s) changed state",
                sent_successfully=False,
                error=str(e)
            )

    def _batch_severity(self) -> AlertSeverity:
        """Determine the highest severity in the batch."""
        has_critical = any(
            entry.change.new_state == DeviceState.DOWN
            for entry in self._batch
        )
        has_warning = any(
            entry.change.new_state == DeviceState.DEGRADED
            for entry in self._batch
        )
        if has_critical:
            return AlertSeverity.CRITICAL
        elif has_warning:
            return AlertSeverity.WARNING
        return AlertSeverity.INFO

    def _build_subject(self) -> str:
        """Build email subject based on batch contents."""
        down_count = sum(1 for e in self._batch if e.change.new_state == DeviceState.DOWN)
        degraded_count = sum(1 for e in self._batch if e.change.new_state == DeviceState.DEGRADED)
        recovered_count = sum(1 for e in self._batch if e.change.new_state == DeviceState.UP and e.change.old_state == DeviceState.DOWN)

        parts = []
        if down_count:
            parts.append(f"🔴 {down_count} DOWN")
        if degraded_count:
            parts.append(f"🟡 {degraded_count} DEGRADED")
        if recovered_count:
            parts.append(f"🟢 {recovered_count} RECOVERED")

        status = ", ".join(parts) if parts else "Status Update"
        return f"[WatchTower] {status}"

    def _build_text_body(self, all_devices: List[Device]) -> str:
        """Build plain text email with changes + full status table."""
        lines = [
            "=" * 60,
            "WATCHTOWER STATUS REPORT",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "=" * 60,
            "",
            "📊 STATE CHANGES",
            "-" * 60,
        ]

        for entry in self._batch:
            emoji = {"up": "🟢", "down": "🔴", "degraded": "🟡"}.get(
                entry.change.new_state.value, "⚪"
            )
            lines.append(
                f"{emoji} {entry.device.name:25s} | "
                f"{entry.change.old_state.value:10s} → {entry.change.new_state.value:10s} | "
                f"{entry.change.reason}"
            )

        lines.extend([
            "",
            "-" * 60,
            "📋 ALL DEVICES STATUS",
            "-" * 60,
        ])

        for device in all_devices:
            emoji = {"up": "🟢", "down": "🔴", "degraded": "🟡", "unknown": "⚪"}.get(
                device.current_state.value, "❓"
            )
            latency = f"{device.last_latency_ms:.1f}ms" if device.last_latency_ms else "N/A"
            lines.append(
                f"{emoji} {device.name:25s} | {device.current_state.value:10s} | {latency:>8s} | {device.ip_address}"
            )

        lines.extend([
            "",
            "-" * 60,
            "WatchTower Infrastructure Monitor",
            f"Report ID: batch-{int(datetime.utcnow().timestamp())}",
        ])

        return "\n".join(lines)

    def _build_html_body(self, all_devices: List[Device]) -> str:
        """Build HTML email with changes + full status table."""
        # Changes table
        changes_rows = ""
        for entry in self._batch:
            color = {"up": "#28a745", "down": "#dc3545", "degraded": "#ffc107"}.get(
                entry.change.new_state.value, "#6c757d"
            )
            changes_rows += f"""
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>{entry.device.name}</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{entry.device.ip_address}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{entry.change.old_state.value.upper()} → <strong style="color: {color};">{entry.change.new_state.value.upper()}</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{entry.change.reason}</td>
                </tr>
            """

        # Full status table
        status_rows = ""
        for device in all_devices:
            color = {"up": "#28a745", "down": "#dc3545", "degraded": "#ffc107", "unknown": "#6c757d"}.get(
                device.current_state.value, "#6c757d"
            )
            latency = f"{device.last_latency_ms:.1f}ms" if device.last_latency_ms else "N/A"
            status_rows += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{device.name}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{device.ip_address}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;"><span style="color: {color}; font-weight: bold;">{device.current_state.value.upper()}</span></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{latency}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{device.location}</td>
                </tr>
            """

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
            <div style="max-width: 700px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="background: #dc3545; color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px;">🗼 WatchTower Status Report</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                </div>

                <div style="padding: 20px;">
                    <h2 style="color: #333; border-bottom: 2px solid #dc3545; padding-bottom: 10px;">📊 State Changes</h2>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                        <thead>
                            <tr style="background: #f8f9fa;">
                                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Device</th>
                                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">IP</th>
                                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Change</th>
                                <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Reason</th>
                            </tr>
                        </thead>
                        <tbody>
                            {changes_rows}
                        </tbody>
                    </table>

                    <h2 style="color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px;">📋 All Devices Status</h2>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f8f9fa;">
                                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Device</th>
                                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">IP</th>
                                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Status</th>
                                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Latency</th>
                                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Location</th>
                            </tr>
                        </thead>
                        <tbody>
                            {status_rows}
                        </tbody>
                    </table>
                </div>

                <div style="background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #6c757d;">
                    WatchTower Infrastructure Monitor • Report ID: batch-{int(datetime.utcnow().timestamp())}
                </div>
            </div>
        </body>
        </html>
        """

    def _send_email(self, subject: str, body_text: str, body_html: str):
        """Send email via SMTP."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_address
        msg["To"] = ", ".join(self.to_addresses)

        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        context = ssl.create_default_context()

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.use_tls:
                server.starttls(context=context)
            if self.username and self.password:
                server.login(self.username, self.password)
            server.sendmail(self.from_address, self.to_addresses, msg.as_string())

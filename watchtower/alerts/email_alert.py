#Email Alert — Sends notifications via SMTP using smtplib.

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional

from watchtower.models import Device, DeviceState, StateChange, AlertLog, AlertSeverity
from watchtower.config import Config


class EmailAlert:
    #Sends email alerts for device state changes.
    
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
    
    def send_alert(self, change: StateChange, device: Device) -> AlertLog:
        if not self.enabled:
            return AlertLog(
                device_id=device.id,
                alert_type="email",
                severity=self._classify_severity(change),
                message="Email alerts disabled in config",
                sent_successfully=False
            )
        
        if not self.to_addresses:
            return AlertLog(
                device_id=device.id,
                alert_type="email",
                severity=self._classify_severity(change),
                message="No recipients configured",
                sent_successfully=False
            )
        
        subject = self._build_subject(change, device)
        body_text = self._build_text_body(change, device)
        body_html = self._build_html_body(change, device)
        
        try:
            self._send_email(subject, body_text, body_html)
            return AlertLog(
                device_id=device.id,
                alert_type="email",
                severity=self._classify_severity(change),
                message=subject,
                sent_successfully=True
            )
        except Exception as e:
            return AlertLog(
                device_id=device.id,
                alert_type="email",
                severity=self._classify_severity(change),
                message=subject,
                sent_successfully=False,
                error=str(e)
            )
    
    def _classify_severity(self, change: StateChange) -> AlertSeverity:
        if change.new_state == DeviceState.DOWN:
            return AlertSeverity.CRITICAL
        elif change.new_state == DeviceState.DEGRADED:
            return AlertSeverity.WARNING
        elif change.old_state == DeviceState.DOWN and change.new_state == DeviceState.UP:
            return AlertSeverity.INFO
        return AlertSeverity.INFO
    
    def _build_subject(self, change: StateChange, device: Device) -> str:
        emoji = {
            DeviceState.UP: "🟢",
            DeviceState.DOWN: "🔴",
            DeviceState.DEGRADED: "🟡",
        }.get(change.new_state, "⚪")
        
        action = {
            DeviceState.UP: "RECOVERED",
            DeviceState.DOWN: "DOWN",
            DeviceState.DEGRADED: "DEGRADED",
        }.get(change.new_state, "STATE CHANGE")
        
        return f"[WatchTower] {emoji} {device.name} is {action}"
    
    def _build_text_body(self, change: StateChange, device: Device) -> str:
        lines = [
            "=" * 50,
            "WATCHTOWER ALERT",
            "=" * 50,
            "",
            f"Device:     {device.name}",
            f"IP Address: {device.ip_address}",
            f"Hostname:   {device.hostname}",
            f"Type:       {device.device_type}",
            f"Location:   {device.location}",
            "",
            f"State:      {change.old_state.value.upper()} → {change.new_state.value.upper()}",
            f"Reason:     {change.reason}",
            f"Time:       {change.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        ]
        
        if change.latency_ms is not None:
            lines.append(f"Latency:    {change.latency_ms:.2f}ms")
        
        lines.extend([
            "",
            "-" * 50,
            "WatchTower Infrastructure Monitor",
            f"Alert ID: {change.device_id}-{int(change.timestamp.timestamp())}",
        ])
        
        return "\n".join(lines)
    
    def _build_html_body(self, change: StateChange, device: Device) -> str:
        color = {
            DeviceState.UP: "#28a745",
            DeviceState.DOWN: "#dc3545",
            DeviceState.DEGRADED: "#ffc107",
        }.get(change.new_state, "#6c757d")
        
        latency_row = f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Latency</strong></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{change.latency_ms:.2f}ms</td>
            </tr>
        """ if change.latency_ms is not None else ""
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="background: {color}; color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px;">🗼 WatchTower Alert</h1>
                </div>
                <div style="padding: 20px;">
                    <h2 style="color: {color}; margin-top: 0;">{device.name}</h2>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd; width: 30%;"><strong>IP Address</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{device.ip_address}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Hostname</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{device.hostname}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Type</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{device.device_type}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Location</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{device.location}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>State Change</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{change.old_state.value.upper()} → <strong style="color: {color};">{change.new_state.value.upper()}</strong></td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Reason</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{change.reason}</td>
                        </tr>
                        {latency_row}
                        <tr>
                            <td style="padding: 8px;"><strong>Time</strong></td>
                            <td style="padding: 8px;">{change.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                        </tr>
                    </table>
                </div>
                <div style="background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #6c757d;">
                    WatchTower Infrastructure Monitor • Alert ID: {change.device_id}-{int(change.timestamp.timestamp())}
                </div>
            </div>
        </body>
        </html>
        """
    
    def _send_email(self, subject: str, body_text: str, body_html: str):
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
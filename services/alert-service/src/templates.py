"""Templates for alert messages."""

from datetime import datetime
from typing import Any

from sentilyze_core import AlertEvent


class AlertTemplates:
    """Message templates for different alert types."""

    @staticmethod
    def format_telegram_message(alert: AlertEvent) -> str:
        """Format alert for Telegram."""
        emoji_map = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🚨",
            "critical": "🔴",
        }
        emoji = emoji_map.get(alert.severity, "📢")

        message = f"{emoji} *{alert.title}*\n\n"
        message += f"{alert.message}\n\n"
        message += f"Severity: `{alert.severity.upper()}`\n"
        message += f"Type: `{alert.alert_type}`\n"
        message += f"Time: `{alert.triggered_at.isoformat()}`\n"

        if alert.data:
            message += "\n*Details:*\n"
            for key, value in alert.data.items():
                if isinstance(value, (dict, list)):
                    value = str(value)[:100]  # Truncate complex values
                message += f"• {key}: `{value}`\n"

        return message

    @staticmethod
    def format_slack_message(alert: AlertEvent) -> dict[str, Any]:
        """Format alert for Slack webhook."""
        color_map = {
            "low": "#36a64f",  # Green
            "medium": "#ff9900",  # Orange
            "high": "#ff0000",  # Red
            "critical": "#990000",  # Dark Red
        }

        fields = []
        if alert.data:
            for key, value in alert.data.items():
                if isinstance(value, (dict, list)):
                    value = str(value)[:100]
                fields.append({
                    "title": key,
                    "value": str(value),
                    "short": True,
                })

        return {
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "#808080"),
                    "title": alert.title,
                    "text": alert.message,
                    "fields": fields,
                    "footer": "Sentilyze Alert Service",
                    "ts": int(datetime.utcnow().timestamp()),
                }
            ]
        }

    @staticmethod
    def format_email_subject(alert: AlertEvent) -> str:
        """Format email subject line."""
        return f"[{alert.severity.upper()}] {alert.title} - Sentilyze Alert"

    @staticmethod
    def format_email_body(alert: AlertEvent) -> str:
        """Format email body (HTML)."""
        html = f"""
        <html>
        <body>
            <h2>{alert.title}</h2>
            <p><strong>Severity:</strong> {alert.severity.upper()}</p>
            <p><strong>Type:</strong> {alert.alert_type}</p>
            <p><strong>Time:</strong> {alert.triggered_at.isoformat()}</p>
            <p>{alert.message}</p>
        """

        if alert.data:
            html += "<h3>Details:</h3><ul>"
            for key, value in alert.data.items():
                if isinstance(value, (dict, list)):
                    value = str(value)[:200]
                html += f"<li><strong>{key}:</strong> {value}</li>"
            html += "</ul>"

        html += """
        </body>
        </html>
        """
        return html

    @staticmethod
    def format_webhook_payload(alert: AlertEvent) -> dict[str, Any]:
        """Format alert for generic webhook."""
        return {
            "alert_id": str(alert.alert_id),
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "data": alert.data,
            "triggered_at": alert.triggered_at.isoformat(),
            "channels": alert.channels,
            "recipients": alert.recipients,
            "tenant_id": alert.tenant_id,
            "sent_at": datetime.utcnow().isoformat(),
        }

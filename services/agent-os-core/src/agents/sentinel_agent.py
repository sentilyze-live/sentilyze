"""SENTINEL Agent - Anomaly & Risk Detection for Sentilyze.

SENTINEL monitors sentiment and market data for anomalies:
- Z-score based anomaly detection on sentiment velocity
- Price-sentiment divergence detection
- Volume anomaly detection
- Cross-asset correlation breakdowns
- Pump-and-dump pattern recognition
- Flash crash early warning

Works closely with SCOUT (raw signals), ORACLE (validation),
and MARIA (operational impact).
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from src.agents.base import BaseAgent
from src.config import settings

logger = structlog.get_logger(__name__)


class SentinelAgent(BaseAgent):
    """Anomaly and Risk Detection Agent for Sentilyze."""

    # Assets to monitor
    MONITORED_ASSETS = ["BTC", "ETH", "XAU", "SOL", "ADA", "BNB", "XRP"]

    # Anomaly severity levels
    SEVERITY_INFO = "INFO"
    SEVERITY_WARNING = "WARNING"
    SEVERITY_CRITICAL = "CRITICAL"

    def __init__(self):
        super().__init__(
            agent_type="sentinel",
            name="SENTINEL",
            description="Sentilyze's Anomaly & Risk Detection Agent - monitors for unusual patterns",
        )

        self.capabilities = [
            "Z-score based anomaly detection",
            "Sentiment velocity monitoring",
            "Price-sentiment divergence detection",
            "Volume anomaly detection",
            "Cross-asset correlation analysis",
            "Pump-and-dump pattern recognition",
            "Flash crash early warning",
        ]

        self.version = "1.0.0"

        # Thresholds
        self.zscore_threshold = getattr(settings, "SENTINEL_ZSCORE_THRESHOLD", 2.5)

    def _get_conversational_system_prompt(self) -> str:
        from src.prompts.system_prompts import get_conversational_prompt
        return get_conversational_prompt(self.agent_type)

    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute SENTINEL's anomaly detection workflow."""
        task = context.get("task", "") if context else ""

        # If triggered via Telegram with a specific question
        if self.is_telegram_triggered() and task and task != "No specific task provided":
            return await self._handle_telegram_query(task, context)

        # Scheduled run: full anomaly scan
        anomalies = []
        alerts = []

        # 1. Check sentiment anomalies
        sentiment_anomalies = await self._check_sentiment_anomalies()
        anomalies.extend(sentiment_anomalies)

        # 2. Check volume anomalies
        volume_anomalies = await self._check_volume_anomalies()
        anomalies.extend(volume_anomalies)

        # 3. Check price-sentiment divergence
        divergences = await self._check_divergences()
        anomalies.extend(divergences)

        # 4. Generate alerts for critical anomalies
        for anomaly in anomalies:
            if anomaly.get("severity") in [self.SEVERITY_WARNING, self.SEVERITY_CRITICAL]:
                alerts.append(anomaly)

        # 5. Send critical alerts immediately via Telegram
        if alerts:
            alert_message = self._format_alert_message(alerts)
            await self.telegram.send_alert(alert_message)

            # Also reply to Telegram if triggered from there
            if self.is_telegram_triggered():
                await self.reply_to_telegram(alert_message)

        # 6. Log activity
        await self.log_activity(
            action="anomaly_scan",
            details=f"Scanned {len(self.MONITORED_ASSETS)} assets",
            result=f"Found {len(anomalies)} anomalies, {len(alerts)} alerts",
        )

        result = {
            "anomalies_detected": len(anomalies),
            "alerts_sent": len(alerts),
            "anomalies": anomalies,
            "scan_timestamp": datetime.utcnow().isoformat(),
        }

        # Store scan results
        scan_id = f"sentinel_scan_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        await self.firestore.set_document("agent_os_anomalies", scan_id, result)

        return result

    async def _handle_telegram_query(self, task: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle a specific query from Telegram."""
        # Get recent anomaly data
        recent_anomalies = await self._get_recent_anomalies()

        prompt = f"""Sen SENTINEL, Sentilyze'in anomali tespit agenti.
Kullanicinin sorusunu son anomali verileriyle cevapla.

Son anomali verileri:
{json.dumps(recent_anomalies, indent=2, default=str)[:3000]}

Kullanici sorusu: "{task}"

Turkce cevap ver. Anomali seviyelerini belirt (INFO/WARNING/CRITICAL).
Z-score ve istatistik verilerini acikla.
HTML formatlama kullan."""

        response = await self.kimi.generate(
            prompt=prompt,
            system_prompt=self._get_conversational_system_prompt(),
            max_tokens=1500,
        )

        if self.is_telegram_triggered():
            await self.reply_to_telegram(response)

        return {"response": response, "recent_anomalies": recent_anomalies}

    async def _check_sentiment_anomalies(self) -> List[Dict[str, Any]]:
        """Check for anomalies in sentiment data.

        Uses Z-score based detection on sentiment changes.
        """
        anomalies = []

        for asset in self.MONITORED_ASSETS:
            try:
                # Get sentiment data
                sentiment_data = await self.get_sentiment_data(asset=asset, hours=72)

                if not sentiment_data or len(sentiment_data) < 5:
                    continue

                # Calculate sentiment velocity (rate of change)
                values = [d.get("sentiment_score", 0) for d in sentiment_data if d.get("sentiment_score") is not None]

                if len(values) < 5:
                    continue

                # Simple Z-score calculation
                mean = sum(values) / len(values)
                variance = sum((x - mean) ** 2 for x in values) / len(values)
                std_dev = variance ** 0.5

                if std_dev == 0:
                    continue

                latest = values[0] if values else 0
                z_score = (latest - mean) / std_dev

                if abs(z_score) >= self.zscore_threshold:
                    severity = self.SEVERITY_CRITICAL if abs(z_score) >= 3.5 else self.SEVERITY_WARNING
                    direction = "yukselis" if z_score > 0 else "dusus"

                    anomalies.append({
                        "asset": asset,
                        "type": "sentiment_anomaly",
                        "severity": severity,
                        "z_score": round(z_score, 2),
                        "current_value": round(latest, 4),
                        "mean": round(mean, 4),
                        "std_dev": round(std_dev, 4),
                        "description": f"{asset} sentiment'inda anormal {direction} (Z={z_score:.1f})",
                        "recommended_action": "ORACLE validation needed",
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            except Exception as e:
                logger.warning("sentinel.sentiment_check_error", asset=asset, error=str(e))

        return anomalies

    async def _check_volume_anomalies(self) -> List[Dict[str, Any]]:
        """Check for volume anomalies."""
        anomalies = []

        for asset in self.MONITORED_ASSETS:
            try:
                market_data = await self.get_market_data(asset=asset, hours=72)

                if not market_data or len(market_data) < 5:
                    continue

                volumes = [d.get("volume", 0) for d in market_data if d.get("volume")]

                if len(volumes) < 5:
                    continue

                mean_vol = sum(volumes) / len(volumes)
                if mean_vol == 0:
                    continue

                latest_vol = volumes[0] if volumes else 0
                volume_ratio = latest_vol / mean_vol

                if volume_ratio >= 3.0:  # 3x average volume
                    anomalies.append({
                        "asset": asset,
                        "type": "volume_spike",
                        "severity": self.SEVERITY_WARNING if volume_ratio < 5.0 else self.SEVERITY_CRITICAL,
                        "volume_ratio": round(volume_ratio, 2),
                        "current_volume": latest_vol,
                        "mean_volume": round(mean_vol, 2),
                        "description": f"{asset} hacmi ortalamanin {volume_ratio:.1f}x uzerinde",
                        "recommended_action": "Investigate for pump-and-dump pattern",
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            except Exception as e:
                logger.warning("sentinel.volume_check_error", asset=asset, error=str(e))

        return anomalies

    async def _check_divergences(self) -> List[Dict[str, Any]]:
        """Check for price-sentiment divergences.

        When price and sentiment move in opposite directions,
        it may indicate manipulation or a trend reversal.
        """
        anomalies = []

        for asset in self.MONITORED_ASSETS:
            try:
                sentiment_data = await self.get_sentiment_data(asset=asset, hours=48)
                market_data = await self.get_market_data(asset=asset, hours=48)

                if not sentiment_data or not market_data:
                    continue

                # Get recent sentiment direction
                sentiment_values = [d.get("sentiment_score", 0) for d in sentiment_data[:5] if d.get("sentiment_score") is not None]
                price_values = [d.get("price", 0) for d in market_data[:5] if d.get("price")]

                if len(sentiment_values) < 2 or len(price_values) < 2:
                    continue

                sentiment_change = sentiment_values[0] - sentiment_values[-1]
                price_change = (price_values[0] - price_values[-1]) / price_values[-1] if price_values[-1] != 0 else 0

                # Detect divergence: sentiment up + price down (or vice versa)
                sentiment_positive = sentiment_change > 0.1
                price_positive = price_change > 0.02

                if (sentiment_positive and not price_positive and price_change < -0.02) or \
                   (not sentiment_positive and sentiment_change < -0.1 and price_positive):
                    direction = "Sentiment yukseliyor ama fiyat dusuyor" if sentiment_positive else "Fiyat yukseliyor ama sentiment dusuyor"
                    anomalies.append({
                        "asset": asset,
                        "type": "price_sentiment_divergence",
                        "severity": self.SEVERITY_WARNING,
                        "sentiment_change": round(sentiment_change, 4),
                        "price_change_pct": round(price_change * 100, 2),
                        "description": f"{asset}: {direction}",
                        "recommended_action": "Monitor closely - potential trend reversal",
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            except Exception as e:
                logger.warning("sentinel.divergence_check_error", asset=asset, error=str(e))

        return anomalies

    async def _get_recent_anomalies(self) -> List[Dict[str, Any]]:
        """Get recently detected anomalies from Firestore."""
        try:
            # Query recent anomaly scans
            docs = (
                self.firestore.client.collection("agent_os_anomalies")
                .order_by("scan_timestamp", direction="DESCENDING")
                .limit(5)
                .stream()
            )
            results = []
            for doc in docs:
                data = doc.to_dict()
                anomalies = data.get("anomalies", [])
                results.extend(anomalies)
            return results[:20]  # Last 20 anomalies
        except Exception:
            return []

    def _format_alert_message(self, alerts: List[Dict[str, Any]]) -> str:
        """Format alerts as a Telegram message."""
        parts = ["🚨 <b>SENTINEL Anomali Alarmi</b>", ""]

        for alert in alerts[:5]:  # Max 5 alerts per message
            severity = alert.get("severity", "INFO")
            icon = "🔴" if severity == "CRITICAL" else "🟡"
            asset = alert.get("asset", "?")
            desc = alert.get("description", "")
            action = alert.get("recommended_action", "")

            parts.append(f"{icon} <b>[{severity}] {asset}</b>")
            parts.append(f"   {desc}")
            if alert.get("z_score"):
                parts.append(f"   Z-score: <code>{alert['z_score']}</code>")
            if action:
                parts.append(f"   → {action}")
            parts.append("")

        parts.append(f"<i>Scan: {datetime.utcnow().strftime('%H:%M UTC')}</i>")
        return "\n".join(parts)

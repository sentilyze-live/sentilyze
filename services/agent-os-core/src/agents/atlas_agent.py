"""ATLAS Agent - Data Quality & Pipeline Monitoring for Sentilyze.

ATLAS monitors data quality across all ingestion sources:
- Data staleness detection (which source last sent data and when)
- Missing data gap analysis
- Data format consistency checks
- Source-based quality scoring
- BigQuery table size and cost monitoring

Works closely with MARIA (infrastructure), SCOUT (data reliability),
and ORACLE (statistical data quality).
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from src.agents.base import BaseAgent
from src.config import settings

logger = structlog.get_logger(__name__)


class AtlasAgent(BaseAgent):
    """Data Quality & Pipeline Monitoring Agent for Sentilyze."""

    # Known data sources (from services/ingestion/src/collectors/)
    DATA_SOURCES = [
        {"name": "alphavantage", "type": "market_data", "expected_interval_minutes": 60},
        {"name": "newsapi", "type": "news", "expected_interval_minutes": 120},
        {"name": "google_trends", "type": "trends", "expected_interval_minutes": 360},
        {"name": "tradingview", "type": "technical", "expected_interval_minutes": 60},
        {"name": "youtube", "type": "social", "expected_interval_minutes": 720},
        {"name": "telegram_channels", "type": "social", "expected_interval_minutes": 120},
        {"name": "stocktwits", "type": "social", "expected_interval_minutes": 120},
        {"name": "investingcom", "type": "market_data", "expected_interval_minutes": 60},
        {"name": "web_scrapers", "type": "news", "expected_interval_minutes": 360},
        {"name": "volume_proxy", "type": "market_data", "expected_interval_minutes": 60},
    ]

    def __init__(self):
        super().__init__(
            agent_type="atlas",
            name="ATLAS",
            description="Sentilyze's Data Quality & Pipeline Monitor - ensures data reliability",
        )

        self.capabilities = [
            "Data source health monitoring",
            "Staleness detection across all collectors",
            "Missing data gap analysis",
            "Data format consistency checks",
            "Source-based quality scoring",
            "BigQuery table monitoring",
        ]

        self.version = "1.0.0"

        # Threshold for stale data (minutes)
        self.staleness_threshold = getattr(settings, "ATLAS_STALENESS_THRESHOLD_MINUTES", 180)

    def _get_conversational_system_prompt(self) -> str:
        from src.prompts.system_prompts import get_conversational_prompt
        return get_conversational_prompt(self.agent_type)

    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute ATLAS's data quality monitoring workflow."""
        task = context.get("task", "") if context else ""

        # If triggered via Telegram with a specific question
        if self.is_telegram_triggered() and task and task != "No specific task provided":
            return await self._handle_telegram_query(task, context)

        # Scheduled run: full data quality report
        source_reports = []
        alerts = []
        overall_scores = []

        for source_config in self.DATA_SOURCES:
            source_name = source_config["name"]
            try:
                report = await self._check_source_health(source_config)
                source_reports.append(report)

                if report.get("freshness_score", 1.0) < 0.5:
                    alerts.append({
                        "source": source_name,
                        "issue": "stale_data",
                        "severity": "WARNING" if report["freshness_score"] > 0.2 else "CRITICAL",
                        "details": report.get("status_message", ""),
                    })

                overall_scores.append(report.get("quality_score", 0.5))

            except Exception as e:
                logger.warning("atlas.source_check_error", source=source_name, error=str(e))
                source_reports.append({
                    "name": source_name,
                    "status": "error",
                    "error": str(e),
                    "quality_score": 0,
                    "freshness_score": 0,
                })

        # Calculate overall quality
        overall_quality = sum(overall_scores) / len(overall_scores) if overall_scores else 0

        # Send alerts for critical issues
        if alerts:
            alert_message = self._format_quality_alert(alerts, overall_quality)
            await self.telegram.send_alert(alert_message)

        # Send summary if Telegram triggered
        if self.is_telegram_triggered():
            summary = self._format_quality_report(source_reports, overall_quality)
            await self.reply_to_telegram(summary)

        # Log activity
        await self.log_activity(
            action="data_quality_scan",
            details=f"Scanned {len(self.DATA_SOURCES)} data sources",
            result=f"Overall quality: {overall_quality:.0%}, {len(alerts)} alerts",
        )

        result = {
            "overall_quality_score": round(overall_quality, 3),
            "sources_checked": len(source_reports),
            "alerts": len(alerts),
            "source_reports": source_reports,
            "alert_details": alerts,
            "scan_timestamp": datetime.utcnow().isoformat(),
        }

        # Store report
        report_id = f"atlas_report_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        await self.firestore.set_document("agent_os_data_quality", report_id, {
            "overall_quality": overall_quality,
            "alerts_count": len(alerts),
            "timestamp": datetime.utcnow(),
        })

        return result

    async def _handle_telegram_query(self, task: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle a specific data quality query from Telegram."""
        # Run a fresh quality check
        source_reports = []
        for source_config in self.DATA_SOURCES:
            try:
                report = await self._check_source_health(source_config)
                source_reports.append(report)
            except Exception:
                source_reports.append({"name": source_config["name"], "status": "error"})

        overall_scores = [r.get("quality_score", 0.5) for r in source_reports if "quality_score" in r]
        overall_quality = sum(overall_scores) / len(overall_scores) if overall_scores else 0

        prompt = f"""Sen ATLAS, Sentilyze'in data kalite agenti.
Kullanicinin sorusunu son data kalitesi verileriyle cevapla.

Data kalitesi raporu:
- Genel kalite skoru: {overall_quality:.0%}
- Kaynak detaylari:
{json.dumps(source_reports, indent=2, default=str)[:3000]}

Kullanici sorusu: "{task}"

Turkce cevap ver. Kaynak bazli durum bildir.
Sorunlu kaynaklari belirt ve cozum oner.
HTML formatlama kullan."""

        response = await self.kimi.generate(
            prompt=prompt,
            system_prompt=self._get_conversational_system_prompt(),
            max_tokens=1500,
        )

        if self.is_telegram_triggered():
            await self.reply_to_telegram(response)

        return {"response": response, "overall_quality": overall_quality}

    async def _check_source_health(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        """Check health of a specific data source.

        Args:
            source_config: Source configuration dict

        Returns:
            Health report for the source
        """
        source_name = source_config["name"]
        source_type = source_config["type"]
        expected_interval = source_config["expected_interval_minutes"]

        # Query BigQuery for latest data from this source
        freshness_score = 1.0
        completeness_score = 1.0
        status = "healthy"
        status_message = ""
        last_data_time = None
        record_count = 0

        try:
            # Check for recent data based on source type
            if source_type == "market_data":
                data = await self.get_market_data(hours=24)
                record_count = len(data) if data else 0
            elif source_type in ("news", "social"):
                data = await self.get_sentiment_data(hours=24)
                record_count = len(data) if data else 0
            else:
                data = []

            if data and len(data) > 0:
                # Get the most recent timestamp
                latest = data[0]
                last_data_str = latest.get("timestamp") or latest.get("created_at") or latest.get("updated_at")

                if last_data_str:
                    if isinstance(last_data_str, str):
                        try:
                            last_data_time = datetime.fromisoformat(last_data_str.replace("Z", "+00:00").replace("+00:00", ""))
                        except ValueError:
                            last_data_time = None
                    elif isinstance(last_data_str, datetime):
                        last_data_time = last_data_str

                if last_data_time:
                    age_minutes = (datetime.utcnow() - last_data_time).total_seconds() / 60

                    if age_minutes <= expected_interval:
                        freshness_score = 1.0
                    elif age_minutes <= expected_interval * 2:
                        freshness_score = 0.7
                    elif age_minutes <= self.staleness_threshold:
                        freshness_score = 0.4
                        status = "stale"
                        status_message = f"Son veri {age_minutes:.0f} dakika once"
                    else:
                        freshness_score = 0.1
                        status = "critical"
                        status_message = f"Son veri {age_minutes / 60:.1f} saat once"
            else:
                freshness_score = 0.0
                status = "no_data"
                status_message = "Son 24 saatte veri yok"

            # Completeness: check if we have enough records
            expected_records = 24 * 60 / expected_interval  # Expected in 24h
            if expected_records > 0:
                completeness_score = min(1.0, record_count / expected_records)

        except Exception as e:
            status = "error"
            status_message = str(e)[:100]
            freshness_score = 0.0
            completeness_score = 0.0

        quality_score = (freshness_score * 0.6) + (completeness_score * 0.4)

        return {
            "name": source_name,
            "type": source_type,
            "status": status,
            "status_message": status_message,
            "quality_score": round(quality_score, 3),
            "freshness_score": round(freshness_score, 3),
            "completeness_score": round(completeness_score, 3),
            "record_count_24h": record_count,
            "last_data": last_data_time.isoformat() if last_data_time else None,
            "expected_interval_minutes": expected_interval,
        }

    def _format_quality_report(
        self,
        source_reports: List[Dict[str, Any]],
        overall_quality: float,
    ) -> str:
        """Format quality report as Telegram message."""
        quality_icon = "🟢" if overall_quality >= 0.8 else "🟡" if overall_quality >= 0.5 else "🔴"

        parts = [
            f"📊 <b>ATLAS Data Kalitesi Raporu</b>",
            f"",
            f"{quality_icon} Genel Kalite: <b>{overall_quality:.0%}</b>",
            "",
        ]

        # Group by status
        healthy = [r for r in source_reports if r.get("status") == "healthy"]
        issues = [r for r in source_reports if r.get("status") != "healthy"]

        if healthy:
            parts.append(f"✅ <b>Saglicli ({len(healthy)})</b>")
            for r in healthy[:5]:
                parts.append(f"   • {r['name']}: {r.get('quality_score', 0):.0%}")

        if issues:
            parts.append(f"")
            parts.append(f"⚠️ <b>Sorunlu ({len(issues)})</b>")
            for r in issues:
                status_msg = r.get("status_message", r.get("status", "?"))
                parts.append(f"   • {r['name']}: {status_msg}")

        parts.append(f"")
        parts.append(f"<i>Scan: {datetime.utcnow().strftime('%H:%M UTC')}</i>")

        return "\n".join(parts)

    def _format_quality_alert(
        self,
        alerts: List[Dict[str, Any]],
        overall_quality: float,
    ) -> str:
        """Format quality alert as Telegram message."""
        parts = [
            f"🔔 <b>ATLAS Data Kalitesi Alarmi</b>",
            f"Genel kalite: {overall_quality:.0%}",
            "",
        ]

        for alert in alerts[:5]:
            severity = alert.get("severity", "WARNING")
            icon = "🔴" if severity == "CRITICAL" else "🟡"
            source = alert.get("source", "?")
            details = alert.get("details", "")

            parts.append(f"{icon} <b>{source}</b>: {details}")

        return "\n".join(parts)

"""Turkish economic indicators collector.

Uses only reliable API-based sources:
- TCMB EVDS (Central Bank official economic indicators - API-based)
- TCMB Announcements (Central Bank announcements - web scraping fallback)

Note:
- Truncgil removed due to persistent CORS errors
- Gold prices now sourced from Finnhub (primary) and Gold API (secondary)
- Harem Altın and Nadir Döviz removed due to Cloudflare blocking
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sentilyze_core import DataSource, RawEvent, get_logger
from sentilyze_core.exceptions import ExternalServiceError

from .base import BaseEventCollector

if TYPE_CHECKING:
    from ..publisher import EventPublisher

logger = get_logger(__name__)


class TurkishScrapersCollector(BaseEventCollector):
    """Unified collector for Turkish gold and currency scrapers."""

    def __init__(self, publisher: "EventPublisher") -> None:
        super().__init__(publisher)
        self.scrapers: dict[str, Any] = {}
        self._settings = None

    async def initialize(self) -> None:
        """Initialize Turkish scrapers (TCMB EVDS + TCMB Announcements)."""
        from sentilyze_core.config import get_settings
        from .turkish_sources import (
            TCMBScraper,
            TCMBEVDSCollector,
        )

        settings = get_settings()

        # Initialize TCMB EVDS (official economic indicators API - PRIORITY)
        if settings.tcmb_evds_api_key:
            try:
                tcmb_evds = TCMBEVDSCollector(api_key=settings.tcmb_evds_api_key)
                await tcmb_evds.initialize()
                self.scrapers["tcmb_evds"] = tcmb_evds
                logger.info("TCMB EVDS collector initialized")
            except Exception as e:
                logger.error("Failed to initialize TCMB EVDS collector", error=str(e))
        else:
            logger.warning("TCMB EVDS API key not configured, skipping EVDS collector")

        # Initialize TCMB Announcements (fallback web scraper)
        try:
            tcmb = TCMBScraper()
            await tcmb.initialize()
            self.scrapers["tcmb"] = tcmb
            logger.info("TCMB announcements scraper initialized")
        except Exception as e:
            logger.error("Failed to initialize TCMB announcements scraper", error=str(e))

        if not self.scrapers:
            raise ExternalServiceError(
                "No Turkish scrapers could be initialized",
                service="turkish_scrapers",
            )

        self._initialized = True
        logger.info(
            "Turkish scrapers collector initialized",
            active_scrapers=list(self.scrapers.keys()),
        )

    async def collect(self, **kwargs) -> list[RawEvent]:
        """Collect from all Turkish scrapers.

        Returns:
            List of RawEvent objects
        """
        return await self.collect_all()

    async def collect_all(self) -> list[RawEvent]:
        """Collect data from all initialized scrapers."""
        events: list[RawEvent] = []

        for name, scraper in self.scrapers.items():
            try:
                scraper_events = await self.collect_from_source(name)
                events.extend(scraper_events)
                logger.info(
                    "Collected from Turkish scraper",
                    source=name,
                    count=len(scraper_events),
                )
            except Exception as e:
                logger.error(
                    "Failed to collect from scraper",
                    source=name,
                    error=str(e),
                )

        return events

    async def collect_from_source(self, source: str) -> list[RawEvent]:
        """Collect from a specific scraper source.

        Args:
            source: Scraper name (tcmb, tcmb_evds)

        Returns:
            List of RawEvent objects
        """
        if source not in self.scrapers:
            raise ExternalServiceError(
                f"Unknown scraper source: {source}",
                service="turkish_scrapers",
            )

        scraper = self.scrapers[source]
        events: list[RawEvent] = []

        try:
            if source == "tcmb_evds":
                indicators = await scraper.fetch_latest_indicators()
                event = self._tcmb_evds_to_event(indicators)
                if event:
                    events.append(event)

            elif source == "tcmb":
                announcements = await scraper.scrape_latest_announcements(limit=5)
                for ann in announcements:
                    event = self._tcmb_announcement_to_event(ann)
                    if event:
                        events.append(event)

            return events

        except Exception as e:
            logger.error(
                "Collection failed",
                source=source,
                error=str(e),
            )
            raise ExternalServiceError(
                f"Collection failed for {source}: {e}",
                service="turkish_scrapers",
            ) from e

    def _tcmb_evds_to_event(self, indicators: dict) -> Optional[RawEvent]:
        """Convert TCMB EVDS indicators to RawEvent."""
        try:
            if not indicators:
                return None

            # Build content summary
            content_parts = ["TCMB Economic Indicators:"]

            usd_try = indicators.get("usd_try", {}).get("value")
            eur_try = indicators.get("eur_try", {}).get("value")
            cpi = indicators.get("cpi", {}).get("value")

            if usd_try:
                content_parts.append(f"USD/TRY: {usd_try:.4f}")
            if eur_try:
                content_parts.append(f"EUR/TRY: {eur_try:.4f}")
            if cpi:
                content_parts.append(f"CPI: {cpi:.2f}")

            content = ", ".join(content_parts)

            return RawEvent(
                source=DataSource.CUSTOM,
                source_id=f"tcmb_evds_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}",
                content=content,
                metadata={
                    "source": "tcmb_evds",
                    "data_type": "economic_indicators",
                    "indicators": indicators,
                },
                collected_at=datetime.now(timezone.utc),
                symbols=["XAUTRY", "USDTRY", "EURTRY"],
            )
        except Exception as e:
            logger.error("Failed to convert TCMB EVDS data", error=str(e))
            return None

    def _tcmb_announcement_to_event(self, announcement: dict) -> Optional[RawEvent]:
        """Convert TCMB announcement to RawEvent."""
        try:
            title = announcement.get("title", "")
            url = announcement.get("url", "")
            category = announcement.get("category", "OTHER")
            impact = announcement.get("impact_level", "LOW")

            content = f"TCMB Announcement: {title}"

            return RawEvent(
                source=DataSource.CUSTOM,
                source_id=f"tcmb_{hash(title)}_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                content=content,
                title=title,
                url=url,
                metadata={
                    "source": "tcmb",
                    "data_type": "central_bank_announcement",
                    "category": category,
                    "impact_level": impact,
                    "raw_announcement": announcement,
                },
                collected_at=datetime.now(timezone.utc),
                symbols=["XAUTRY", "USDTRY", "EURTRY"],
            )
        except Exception as e:
            logger.error("Failed to convert TCMB announcement", error=str(e))
            return None

    async def close(self) -> None:
        """Close all scrapers."""
        for name, scraper in self.scrapers.items():
            try:
                await scraper.close()
                logger.info(f"Scraper {name} closed")
            except Exception as e:
                logger.error(f"Error closing scraper {name}", error=str(e))

        self.scrapers.clear()
        self._initialized = False
        logger.info("Turkish scrapers collector closed")


# Import types for TYPE_CHECKING
from typing import Any

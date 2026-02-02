"""Turkish gold and currency scrapers collector.

Uses only reliable API-based sources:
- Truncgil Finans API (reliable API-based)
- TCMB (Central Bank announcements)

Note: Harem Altın and Nadir Döviz scrapers removed due to Cloudflare blocking.
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
        """Initialize Turkish scrapers (Truncgil + TCMB only)."""
        from .turkish_sources import (
            TruncgilScraper,
            TCMBScraper,
        )

        # Initialize Truncgil (reliable API)
        try:
            truncgil = TruncgilScraper()
            await truncgil.initialize()
            self.scrapers["truncgil"] = truncgil
            logger.info("Truncgil scraper initialized")
        except Exception as e:
            logger.error("Failed to initialize Truncgil scraper", error=str(e))

        # Initialize TCMB (Central Bank)
        try:
            tcmb = TCMBScraper()
            await tcmb.initialize()
            self.scrapers["tcmb"] = tcmb
            logger.info("TCMB scraper initialized")
        except Exception as e:
            logger.error("Failed to initialize TCMB scraper", error=str(e))

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
            source: Scraper name (truncgil, tcmb)

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
            if source == "truncgil":
                data = await scraper.scrape_prices()
                event = self._truncgil_to_event(data)
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

    def _truncgil_to_event(self, data: dict) -> Optional[RawEvent]:
        """Convert Truncgil data to RawEvent."""
        try:
            altin = data.get("altin_try", {})
            ons = data.get("ons", {})
            dolar = data.get("dolar", {})
            euro = data.get("euro", {})

            content = (
                f"Gram Altın: {altin.get('satis')} TRY, "
                f"Ons: {ons.get('satis')} USD, "
                f"Dolar: {dolar.get('satis')} TRY, "
                f"Euro: {euro.get('satis')} TRY"
            )

            return RawEvent(
                source=DataSource.CUSTOM,
                source_id=f"truncgil_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                content=content,
                metadata={
                    "source": "truncgil",
                    "data_type": "turkish_gold_prices",
                    "prices": {
                        "gram_altin": altin,
                        "ons": ons,
                        "dolar": dolar,
                        "euro": euro,
                    },
                    "raw_data": data,
                },
                collected_at=datetime.now(timezone.utc),
                symbols=["XAUTRY", "XAUUSD", "USDTRY", "EURTRY"],
            )
        except Exception as e:
            logger.error("Failed to convert Truncgil data", error=str(e))
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

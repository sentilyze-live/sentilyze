"""TCMB (Türkiye Cumhuriyet Merkez Bankası) scraper.

Scrapes key economic indicators and policy announcements from TCMB:
- Interest rate decisions (Politika Faizi)
- Foreign exchange reserves
- Inflation expectations
- Important announcements
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from sentilyze_core import get_logger
from sentilyze_core.exceptions import ExternalServiceError

logger = get_logger(__name__)

TCMB_BASE_URL = "https://www.tcmb.gov.tr"
TCMB_ANNOUNCEMENTS_URL = f"{TCMB_BASE_URL}/wps/wcm/connect/tr/tcmb+tr/main+menu/duyurular"


class TCMBScraper:
    """Scraper for TCMB economic data and announcements."""

    def __init__(self) -> None:
        self.client: Optional[httpx.AsyncClient] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize HTTP client."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        self._initialized = True
        logger.info("TCMB scraper initialized")

    @property
    def is_initialized(self) -> bool:
        """Check if scraper is initialized."""
        return self._initialized

    async def scrape_latest_announcements(self, limit: int = 5) -> List[Dict]:
        """Scrape latest TCMB announcements.

        Args:
            limit: Maximum number of announcements to return

        Returns:
            List of announcements
        """
        if not self._initialized or not self.client:
            raise ExternalServiceError(
                "Scraper not initialized",
                service="tcmb",
            )

        try:
            response = await self.client.get(TCMB_ANNOUNCEMENTS_URL)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            announcements = self._extract_announcements(soup, limit)

            logger.info("TCMB announcements scraped", count=len(announcements))
            return announcements

        except httpx.HTTPStatusError as e:
            logger.error("TCMB HTTP error", status_code=e.response.status_code)
            raise ExternalServiceError(
                f"HTTP {e.response.status_code}",
                service="tcmb",
            ) from e
        except Exception as e:
            logger.error("TCMB scraping failed", error=str(e))
            raise ExternalServiceError(
                f"Scraping failed: {e}",
                service="tcmb",
            ) from e

    def _extract_announcements(self, soup: BeautifulSoup, limit: int) -> List[Dict]:
        """Extract announcements from HTML."""
        announcements = []

        announcement_links = soup.find_all('a', href=True, limit=limit * 2)

        for link in announcement_links[:limit]:
            try:
                title = link.get_text(strip=True)
                url = link.get('href', '')

                if not title or len(title) < 10:
                    continue

                if url and not url.startswith('http'):
                    url = f"{TCMB_BASE_URL}{url}"

                is_relevant = self._is_relevant_announcement(title)

                if is_relevant:
                    announcements.append({
                        "title": title,
                        "url": url,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "source": "tcmb",
                        "category": self._categorize_announcement(title),
                        "impact_level": self._assess_impact_level(title),
                    })

            except Exception as e:
                logger.warning(f"Failed to parse announcement: {e}")
                continue

        return announcements[:limit]

    def _is_relevant_announcement(self, title: str) -> bool:
        """Check if announcement is relevant to gold prediction."""
        title_lower = title.lower()

        keywords = [
            "faiz",
            "politika",
            "para politikası",
            "enflasyon",
            "rezerv",
            "döviz",
            "piyasa",
            "likidite",
            "kur korumalı",
        ]

        return any(keyword in title_lower for keyword in keywords)

    def _categorize_announcement(self, title: str) -> str:
        """Categorize announcement type."""
        title_lower = title.lower()

        if "faiz" in title_lower or "politika faizi" in title_lower:
            return "INTEREST_RATE"
        elif "rezerv" in title_lower:
            return "RESERVES"
        elif "enflasyon" in title_lower:
            return "INFLATION"
        elif "kur korumalı" in title_lower or "kkm" in title_lower:
            return "FX_PROTECTED_DEPOSITS"
        elif "likidite" in title_lower:
            return "LIQUIDITY"
        else:
            return "OTHER"

    def _assess_impact_level(self, title: str) -> str:
        """Assess impact level of announcement."""
        title_lower = title.lower()

        high_impact = [
            "faiz kararı",
            "politika faizi",
            "para politikası kurulu",
            "ppk",
        ]

        medium_impact = [
            "rezerv",
            "likidite",
            "kur korumalı",
        ]

        if any(keyword in title_lower for keyword in high_impact):
            return "HIGH"
        elif any(keyword in title_lower for keyword in medium_impact):
            return "MEDIUM"
        else:
            return "LOW"

    async def close(self) -> None:
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            self._initialized = False
            logger.info("TCMB scraper closed")

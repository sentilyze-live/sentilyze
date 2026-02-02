"""Truncgil Finans API scraper for Turkish market prices.

Uses Truncgil Finans public API to fetch:
- Gram gold (24 karat)
- Quarter gold
- USD/TRY
- EUR/TRY

API: https://finans.truncgil.com/today.json
"""

from datetime import datetime, timezone
from typing import Optional

import httpx

from sentilyze_core import get_logger
from sentilyze_core.exceptions import ExternalServiceError

logger = get_logger(__name__)

TRUNCGIL_API_URL = "https://finans.truncgil.com/today.json"


class TruncgilScraper:
    """Scraper for Truncgil Finans API - reliable Turkish market data."""

    def __init__(self) -> None:
        self.client: Optional[httpx.AsyncClient] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize HTTP client."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            headers={
                "User-Agent": "Sentilyze/4.0 (https://sentilyze.live)",
            },
        )
        self._initialized = True
        logger.info("Truncgil scraper initialized")

    @property
    def is_initialized(self) -> bool:
        """Check if scraper is initialized."""
        return self._initialized

    async def scrape_prices(self) -> dict:
        """Scrape prices from Truncgil Finans API.

        Returns:
            Dictionary with gold and currency prices in Turkish format
        """
        if not self._initialized or not self.client:
            raise ExternalServiceError(
                "Scraper not initialized",
                service="truncgil",
            )

        try:
            response = await self.client.get(TRUNCGIL_API_URL)
            response.raise_for_status()
            data = response.json()

            gram_altin = data.get("gram-altin", {})
            ceyrek_altin = data.get("ceyrek-altin", {})
            usd = data.get("USD", {})
            eur = data.get("EUR", {})
            ons = data.get("ons", {})

            gram_alis = self._parse_price(gram_altin.get("Alış"))
            gram_satis = self._parse_price(gram_altin.get("Satış"))

            ceyrek_alis = self._parse_price(ceyrek_altin.get("Alış"))
            ceyrek_satis = self._parse_price(ceyrek_altin.get("Satış"))

            usd_alis = self._parse_price(usd.get("Alış"))
            usd_satis = self._parse_price(usd.get("Satış"))

            eur_alis = self._parse_price(eur.get("Alış"))
            eur_satis = self._parse_price(eur.get("Satış"))

            ons_str = ons.get("Satış", "")
            if ons_str and ons_str.startswith("$"):
                ons_satis = self._parse_price(ons_str[1:])
                ons_alis = self._parse_price(ons.get("Alış", "")[1:] if ons.get("Alış", "").startswith("$") else ons.get("Alış"))
            else:
                ons_alis = None
                ons_satis = None

            prices = {
                "altin_try": {
                    "alis": gram_alis,
                    "satis": gram_satis,
                },
                "ceyrek": {
                    "alis": ceyrek_alis,
                    "satis": ceyrek_satis,
                },
                "ons": {
                    "alis": ons_alis,
                    "satis": ons_satis,
                },
                "dolar": {
                    "alis": usd_alis,
                    "satis": usd_satis,
                },
                "euro": {
                    "alis": eur_alis,
                    "satis": eur_satis,
                },
                "timestamp": data.get("Update_Date", datetime.now(timezone.utc).isoformat()),
                "source": "truncgil",
            }

            logger.info(
                "Truncgil prices fetched",
                gram_try=gram_satis,
                usd_try=usd_satis,
            )
            return prices

        except httpx.HTTPStatusError as e:
            logger.error("Truncgil API error", status=e.response.status_code)
            raise ExternalServiceError(
                f"Truncgil API error: {e.response.status_code}",
                service="truncgil",
            ) from e
        except Exception as e:
            logger.error("Truncgil scraping failed", error=str(e))
            raise ExternalServiceError(
                f"Truncgil failed: {e}",
                service="truncgil",
            ) from e

    def _parse_price(self, price_str: Optional[str]) -> Optional[float]:
        """Parse price string to float (Turkish format: "6.786,60")."""
        if not price_str:
            return None
        try:
            price_str = str(price_str).replace(".", "")
            price_str = price_str.replace(",", ".")
            return round(float(price_str), 2)
        except (ValueError, TypeError):
            return None

    async def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            self._initialized = False
            logger.info("Truncgil scraper closed")

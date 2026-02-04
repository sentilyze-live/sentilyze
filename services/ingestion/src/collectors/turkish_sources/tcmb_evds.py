"""TCMB EVDS (Electronic Data Distribution System) API collector.

Fetches official economic indicators from Turkish Central Bank:
- USD/TRY and EUR/TRY exchange rates
- Policy interest rates
- Inflation rates (CPI/TUFE)
- Foreign exchange reserves
- Gold reserves

API Documentation: https://evds2.tcmb.gov.tr/index.php?/evds/userDocs
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import httpx

from sentilyze_core import get_logger
from sentilyze_core.exceptions import ExternalServiceError

logger = get_logger(__name__)

# TCMB EVDS API Base URL
EVDS_BASE_URL = "https://evds2.tcmb.gov.tr/service/evds"

# Common EVDS series codes for gold-related analysis
# Verified working codes (tested 2026-02-05)
EVDS_SERIES = {
    # Exchange Rates (Indicative Daily)
    "usd_try": "TP.DK.USD.A",  # USD Buying Rate (TRY) - Working!
    "eur_try": "TP.DK.EUR.A",  # EUR Buying Rate (TRY) - Working!

    # Consumer Price Index (TUFE)
    "cpi": "TP.FG.J0",  # CPI General Index - Working!

    # TODO: Find correct series codes for:
    # - Policy interest rate
    # - Foreign exchange reserves
    # - Gold reserves
}


class TCMBEVDSCollector:
    """Collector for TCMB EVDS API - official Turkish economic data."""

    def __init__(self, api_key: str) -> None:
        """Initialize TCMB EVDS collector.

        Args:
            api_key: TCMB EVDS API key
        """
        self.api_key = api_key
        self.client: Optional[httpx.AsyncClient] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize HTTP client."""
        if not self.api_key:
            raise ExternalServiceError(
                "TCMB EVDS API key is required",
                service="tcmb_evds",
            )

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={
                "User-Agent": "Sentilyze/4.0 (https://sentilyze.live)",
                "key": self.api_key,  # EVDS requires API key in header
            },
        )
        self._initialized = True
        logger.info("TCMB EVDS collector initialized")

    @property
    def is_initialized(self) -> bool:
        """Check if collector is initialized."""
        return self._initialized

    async def fetch_series(
        self,
        series_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        aggregation: str = "avg",
        formulas: str = "0",
        frequency: str = "1",  # 1=Daily, 2=Working days, 3=Weekly, 4=Monthly
    ) -> Dict:
        """Fetch a single time series from EVDS.

        Args:
            series_code: EVDS series code (e.g., "TP.DK.USD.A.YTL")
            start_date: Start date in DD-MM-YYYY format (default: 30 days ago)
            end_date: End date in DD-MM-YYYY format (default: today)
            aggregation: Aggregation type (avg, min, max, first, last, sum)
            formulas: Formula operations (0=none, 1=level, 2=percentage change, etc.)
            frequency: Data frequency

        Returns:
            Dictionary with series data
        """
        if not self._initialized or not self.client:
            raise ExternalServiceError(
                "Collector not initialized",
                service="tcmb_evds",
            )

        # Default date range: last 30 days
        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%d-%m-%Y")
        if not end_date:
            end_date = datetime.now(timezone.utc).strftime("%d-%m-%Y")

        # Build request URL (EVDS uses non-standard query format)
        url = (
            f"{EVDS_BASE_URL}?"
            f"series={series_code}&"
            f"startDate={start_date}&"
            f"endDate={end_date}&"
            f"type=json&"
            f"aggregationTypes={aggregation}&"
            f"formulas={formulas}&"
            f"frequency={frequency}"
        )

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()

            logger.info(
                "EVDS series fetched",
                series=series_code,
                items=len(data.get("items", [])),
            )
            return data

        except httpx.HTTPStatusError as e:
            logger.error(
                "EVDS API HTTP error",
                status_code=e.response.status_code,
                series=series_code,
            )
            raise ExternalServiceError(
                f"EVDS API HTTP {e.response.status_code}",
                service="tcmb_evds",
            ) from e
        except Exception as e:
            logger.error("EVDS API request failed", error=str(e), series=series_code)
            raise ExternalServiceError(
                f"EVDS API failed: {e}",
                service="tcmb_evds",
            ) from e

    async def fetch_latest_indicators(self) -> Dict[str, any]:
        """Fetch latest values for all configured economic indicators.

        Returns:
            Dictionary with latest indicator values
        """
        indicators = {}

        # Use last 7 days to ensure we get the latest value
        end_date = datetime.now(timezone.utc).strftime("%d-%m-%Y")
        start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%d-%m-%Y")

        for indicator_name, series_code in EVDS_SERIES.items():
            try:
                data = await self.fetch_series(
                    series_code=series_code,
                    start_date=start_date,
                    end_date=end_date,
                    frequency="1",  # Daily
                )

                items = data.get("items", [])
                if items:
                    # Get the most recent data point
                    latest = items[-1]
                    indicators[indicator_name] = {
                        "value": self._extract_value(latest, series_code),
                        "date": latest.get("Tarih", latest.get("UNIXTIME")),
                        "series_code": series_code,
                    }
                    logger.info(
                        f"Fetched {indicator_name}",
                        value=indicators[indicator_name]["value"],
                    )
                else:
                    logger.warning(f"No data returned for {indicator_name}")

            except Exception as e:
                logger.error(
                    f"Failed to fetch {indicator_name}",
                    series=series_code,
                    error=str(e),
                )
                # Continue with other indicators
                continue

        return indicators

    def _extract_value(self, item: Dict, series_code: str) -> Optional[float]:
        """Extract numeric value from EVDS item.

        The field name in the response uses underscores instead of dots.
        Example: TP.DK.USD.A -> TP_DK_USD_A
        """
        # Convert series code to field name format (dots to underscores)
        field_name = series_code.replace(".", "_")

        # Try exact match first
        if field_name in item:
            value = item[field_name]
        else:
            # Fallback: find any numeric field (skip Tarih/UNIXTIME)
            value = None
            for key, val in item.items():
                if key not in ["Tarih", "UNIXTIME", "Date"] and val is not None:
                    value = val
                    break

        # Convert to float if possible
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert value to float: {value}")
                return None

        return None

    async def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            self._initialized = False
            logger.info("TCMB EVDS collector closed")

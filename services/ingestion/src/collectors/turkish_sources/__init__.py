"""Turkish scrapers sources package.

Individual scrapers for Turkish economic data sources.

Note:
- Truncgil removed due to persistent CORS errors
- Gold prices now from Finnhub (primary) and Gold API (secondary)
- Harem Altın and Nadir Döviz removed due to Cloudflare blocking
"""

from .tcmb import TCMBScraper
from .tcmb_evds import TCMBEVDSCollector

__all__ = [
    "TCMBScraper",
    "TCMBEVDSCollector",
]

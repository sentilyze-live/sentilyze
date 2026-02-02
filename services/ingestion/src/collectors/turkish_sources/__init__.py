"""Turkish scrapers sources package.

Individual scrapers for Turkish gold and currency sources.
Note: Harem Altın and Nadir Döviz removed due to Cloudflare blocking.
"""

from .truncgil import TruncgilScraper
from .tcmb import TCMBScraper

__all__ = [
    "TruncgilScraper",
    "TCMBScraper",
]

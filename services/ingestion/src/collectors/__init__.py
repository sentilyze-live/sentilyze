"""Collector registry for unified ingestion service."""

from .base import BaseCollector, BaseEventCollector, BaseStreamCollector
from .binance import BinanceCollector
from .cryptopanic import CryptoPanicCollector
from .finnhub import FinnhubNewsCollector
from .fred import FredCollector
from .goldapi import GoldAPICollector
from .lunarcrush import LunarCrushCollector
from .reddit import RedditCollector
from .rss import RSSCollector
from .santiment import SantimentCollector
from .turkish_scrapers import TurkishScrapersCollector

__all__ = [
    "BaseCollector",
    "BaseEventCollector",
    "BaseStreamCollector",
    "BinanceCollector",
    "CryptoPanicCollector",
    "FinnhubNewsCollector",
    "FredCollector",
    "GoldAPICollector",
    "LunarCrushCollector",
    "RedditCollector",
    "RSSCollector",
    "SantimentCollector",
    "TurkishScrapersCollector",
]

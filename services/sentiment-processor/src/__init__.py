"""Sentiment Processor package."""

from .config import MarketType, AnalysisMode, SentimentLabel
from .analyzer import UnifiedSentimentAnalyzer
from .analyzer_crypto import CryptoSentimentAnalyzer
from .analyzer_gold import GoldSentimentAnalyzer
from .cache import SentimentCache
from .publisher import ResultsPublisher
from .consumer import PubSubConsumer
from .transformers import DataTransformer, SilverLayerTransformer

__version__ = "3.0.0"
__all__ = [
    "MarketType",
    "AnalysisMode",
    "SentimentLabel",
    "UnifiedSentimentAnalyzer",
    "CryptoSentimentAnalyzer",
    "GoldSentimentAnalyzer",
    "SentimentCache",
    "ResultsPublisher",
    "PubSubConsumer",
    "DataTransformer",
    "SilverLayerTransformer",
]

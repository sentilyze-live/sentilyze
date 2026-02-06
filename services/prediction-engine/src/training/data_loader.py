"""Training data loader from BigQuery.

Fetches historical gold prices, economic indicators, and sentiment scores
to build training datasets for LSTM, XGBoost, Random Forest, and ARIMA models.
"""

from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from sentilyze_core import get_logger, get_settings

logger = get_logger(__name__)
settings = get_settings()


class TrainingDataLoader:
    """Load and prepare training data from BigQuery."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google.cloud import bigquery
            self._client = bigquery.Client(project=settings.google_cloud_project)
        return self._client

    async def load_price_history(
        self,
        symbol: str = "XAU",
        days: int = 365,
    ) -> np.ndarray:
        """Load historical prices from BigQuery.

        Returns:
            Array of shape (N,) with closing prices, oldest first.
        """
        client = self._get_client()
        query = """
        SELECT
            CAST(JSON_EXTRACT_SCALAR(payload, '$.price') AS FLOAT64) as price,
            timestamp
        FROM `{project}.{dataset}.raw_events`
        WHERE symbol LIKE @symbol_pattern
          AND timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
          AND JSON_EXTRACT_SCALAR(payload, '$.price') IS NOT NULL
        ORDER BY timestamp ASC
        """.format(
            project=settings.google_cloud_project,
            dataset=settings.bigquery_dataset,
        )

        job_config = self._make_job_config([
            ("symbol_pattern", "STRING", f"%{symbol}%"),
            ("days", "INT64", days),
        ])

        results = client.query(query, job_config=job_config).result()
        prices = [float(row.price) for row in results if row.price]

        if not prices:
            logger.warning("No price data found", symbol=symbol, days=days)
            return np.array([])

        logger.info("Loaded price history", symbol=symbol, count=len(prices))
        return np.array(prices, dtype=np.float64)

    async def load_economic_history(self, days: int = 365) -> dict[str, np.ndarray]:
        """Load historical economic indicators from BigQuery.

        Returns:
            Dict mapping indicator name to time series array.
        """
        client = self._get_client()
        query = """
        SELECT
            symbol,
            CAST(JSON_EXTRACT_SCALAR(payload, '$.value') AS FLOAT64) as value,
            timestamp
        FROM `{project}.{dataset}.raw_events`
        WHERE event_type IN ('economic_data', 'market_data', 'volatility_index',
                             'equity_index', 'currency_index')
          AND timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
          AND symbol IN ('DTWEXBGS', 'DGS10', 'CPIAUCSL', 'CL=F', '^VIX',
                         '^GSPC', 'DX-Y.NYB', 'WTI')
          AND JSON_EXTRACT_SCALAR(payload, '$.value') IS NOT NULL
        ORDER BY timestamp ASC
        """.format(
            project=settings.google_cloud_project,
            dataset=settings.bigquery_dataset,
        )

        job_config = self._make_job_config([("days", "INT64", days)])
        results = client.query(query, job_config=job_config).result()

        symbol_map = {
            'DTWEXBGS': 'dxy', 'DX-Y.NYB': 'dxy',
            'DGS10': 'treasury_10y',
            'CPIAUCSL': 'cpi',
            'CL=F': 'wti_oil', 'WTI': 'wti_oil',
            '^VIX': 'vix',
            '^GSPC': 'sp500',
        }

        data: dict[str, list[float]] = {
            'dxy': [], 'treasury_10y': [], 'cpi': [],
            'wti_oil': [], 'vix': [], 'sp500': [],
        }

        for row in results:
            key = symbol_map.get(row.symbol)
            if key and row.value:
                data[key].append(float(row.value))

        result = {k: np.array(v, dtype=np.float64) for k, v in data.items()}
        logger.info("Loaded economic history", indicators={k: len(v) for k, v in result.items()})
        return result

    async def load_sentiment_history(
        self,
        symbol: str = "XAU",
        days: int = 365,
    ) -> np.ndarray:
        """Load historical sentiment scores from BigQuery.

        Returns:
            Array of shape (N,) with sentiment scores (-1 to 1).
        """
        client = self._get_client()
        query = """
        SELECT
            AVG(sentiment_score) as avg_score,
            TIMESTAMP_TRUNC(processed_at, HOUR) as hour
        FROM `{project}.{dataset}.sentiment_analysis`
        WHERE @symbol IN UNNEST(symbols)
          AND processed_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
        GROUP BY hour
        ORDER BY hour ASC
        """.format(
            project=settings.google_cloud_project,
            dataset=settings.bigquery_dataset,
        )

        job_config = self._make_job_config([
            ("symbol", "STRING", symbol),
            ("days", "INT64", days),
        ])

        results = client.query(query, job_config=job_config).result()
        scores = [float(row.avg_score) for row in results if row.avg_score is not None]

        logger.info("Loaded sentiment history", symbol=symbol, count=len(scores))
        return np.array(scores, dtype=np.float64) if scores else np.array([])

    async def build_training_dataset(
        self,
        symbol: str = "XAU",
        days: int = 180,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Build complete training dataset with features and targets.

        Returns:
            (X, y) where:
            - X: Feature matrix (N, 15) with technical + economic + derived features
            - y: Target values (N,) - price change signal (-1 to 1)
        """
        prices = await self.load_price_history(symbol, days)
        if len(prices) < 100:
            raise ValueError(f"Insufficient price data: {len(prices)} samples (need 100+)")

        economic = await self.load_economic_history(days)
        sentiment = await self.load_sentiment_history(symbol, days)

        n = len(prices)

        # Align economic data to price data length via interpolation
        dxy = self._align_series(economic.get('dxy', np.array([])), n, default=100.0)
        treasury = self._align_series(economic.get('treasury_10y', np.array([])), n, default=3.0)
        cpi = self._align_series(economic.get('cpi', np.array([])), n, default=300.0)
        oil = self._align_series(economic.get('wti_oil', np.array([])), n, default=70.0)
        vix = self._align_series(economic.get('vix', np.array([])), n, default=15.0)
        sp500 = self._align_series(economic.get('sp500', np.array([])), n, default=4500.0)
        sent = self._align_series(sentiment, n, default=0.0)

        # Calculate technical indicators for each point
        rsi = self._rolling_rsi(prices, period=14)
        macd = self._rolling_macd(prices)
        ema_short = self._ema(prices, 9)
        ema_medium = self._ema(prices, 21)

        # Normalize economic data
        dxy_norm = dxy / 100.0
        treasury_norm = treasury / 5.0
        cpi_norm = cpi / 300.0
        oil_norm = oil / 100.0
        vix_norm = vix / 30.0
        sp500_norm = sp500 / 5000.0

        # Build feature matrix (15 features)
        X = np.column_stack([
            # Technical (5)
            rsi,
            macd,
            ema_short,
            ema_medium,
            sent,
            # Economic (6)
            dxy_norm,
            treasury_norm,
            cpi_norm,
            oil_norm,
            vix_norm,
            sp500_norm,
            # Derived (4)
            ema_short - ema_medium,                         # EMA spread
            dxy_norm * treasury_norm,                       # USD-interest interaction
            vix_norm / (sp500_norm + 0.01),                # Fear-equity ratio
            cpi_norm * oil_norm,                            # Inflation-energy
        ])

        # Build targets: future price change as signal (-1 to 1)
        y = np.zeros(n)
        for i in range(n - 1):
            change = (prices[i + 1] - prices[i]) / prices[i]
            y[i] = np.clip(change * 100, -1, 1)  # Scale percentage change

        # Remove last sample (no future target)
        X = X[:-1]
        y = y[:-1]

        # Remove rows with NaN
        valid_mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
        X = X[valid_mask]
        y = y[valid_mask]

        logger.info("Built training dataset", samples=len(X), features=X.shape[1])
        return X, y

    async def build_lstm_dataset(
        self,
        symbol: str = "XAU",
        days: int = 180,
        lookback: int = 30,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Build LSTM-specific dataset with lookback sequences.

        Returns:
            (X, y) where:
            - X: (N, lookback, 10) feature sequences
            - y: (N,) target values (next price)
        """
        prices = await self.load_price_history(symbol, days)
        if len(prices) < lookback + 50:
            raise ValueError(f"Insufficient data for LSTM: {len(prices)} (need {lookback + 50}+)")

        economic = await self.load_economic_history(days)
        n = len(prices)

        dxy = self._align_series(economic.get('dxy', np.array([])), n, default=100.0)
        treasury = self._align_series(economic.get('treasury_10y', np.array([])), n, default=3.0)
        cpi = self._align_series(economic.get('cpi', np.array([])), n, default=300.0)
        oil = self._align_series(economic.get('wti_oil', np.array([])), n, default=70.0)
        vix = self._align_series(economic.get('vix', np.array([])), n, default=15.0)
        sp500 = self._align_series(economic.get('sp500', np.array([])), n, default=4500.0)

        rsi = self._rolling_rsi(prices, period=14)
        macd = self._rolling_macd(prices)
        ema_short = self._ema(prices, 9)

        # 10-feature multivariate time series
        data = np.column_stack([
            prices, dxy, treasury, cpi, oil, vix, sp500, rsi, macd, ema_short,
        ])

        # Remove NaN rows
        valid_mask = ~np.isnan(data).any(axis=1)
        data = data[valid_mask]

        # Create sequences
        X, y = [], []
        for i in range(lookback, len(data)):
            X.append(data[i - lookback:i])
            y.append(data[i, 0])  # Target = gold price

        logger.info("Built LSTM dataset", sequences=len(X), lookback=lookback)
        return np.array(X), np.array(y)

    def _align_series(
        self,
        series: np.ndarray,
        target_len: int,
        default: float,
    ) -> np.ndarray:
        """Align a time series to target length via interpolation."""
        if len(series) == 0:
            return np.full(target_len, default, dtype=np.float64)
        if len(series) == target_len:
            return series
        if len(series) == 1:
            return np.full(target_len, series[0], dtype=np.float64)

        indices = np.linspace(0, len(series) - 1, target_len)
        return np.interp(indices, np.arange(len(series)), series)

    def _rolling_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate rolling RSI for entire price series."""
        n = len(prices)
        rsi = np.full(n, 50.0)
        deltas = np.diff(prices)

        for i in range(period, n):
            window = deltas[max(0, i - period):i]
            gains = np.where(window > 0, window, 0)
            losses = np.where(window < 0, -window, 0)
            avg_gain = np.mean(gains) if len(gains) > 0 else 0
            avg_loss = np.mean(losses) if len(losses) > 0 else 0
            if avg_loss == 0:
                rsi[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi[i] = 100 - (100 / (1 + rs))

        return rsi

    def _rolling_macd(self, prices: np.ndarray) -> np.ndarray:
        """Calculate rolling MACD histogram for entire price series."""
        ema_fast = self._ema_series(prices, 12)
        ema_slow = self._ema_series(prices, 26)
        macd_line = ema_fast - ema_slow
        signal_line = self._ema_series(macd_line, 9)
        return macd_line - signal_line

    def _ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA returning last value for each point."""
        return self._ema_series(prices, period)

    def _ema_series(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate full EMA series."""
        n = len(data)
        ema = np.full(n, np.nan)
        if n < period:
            return ema

        multiplier = 2 / (period + 1)
        ema[period - 1] = np.mean(data[:period])
        for i in range(period, n):
            ema[i] = (data[i] - ema[i - 1]) * multiplier + ema[i - 1]

        # Forward fill NaN at start
        first_valid = period - 1
        ema[:first_valid] = ema[first_valid]

        return ema

    def _make_job_config(self, params: list[tuple]):
        """Create BigQuery job config with query parameters."""
        from google.cloud import bigquery

        return bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(name, type_, value)
                for name, type_, value in params
            ]
        )

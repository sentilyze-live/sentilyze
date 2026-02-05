SELECT
  DATE(timestamp) as date,
  asset_symbol,
  AVG(current_price) as avg_price,
  MAX(current_price) as high_price,
  MIN(current_price) as low_price,
  AVG(volatility_index) as avg_volatility,
  AVG(volume_24h) as avg_volume,
  AVG(rsi) as avg_rsi,
  AVG(CAST(JSON_EXTRACT_SCALAR(correlation_data, '$.usd_strength') AS FLOAT64)) as avg_usd_correlation,
  AVG(CAST(JSON_EXTRACT_SCALAR(correlation_data, '$.treasury_yield') AS FLOAT64)) as avg_yield_correlation,

  -- Economic indicators (from yfinance and FRED collectors)
  AVG(CASE WHEN symbol IN ('DX-Y.NYB', 'DTWEXBGS') THEN current_price END) as avg_dxy,
  AVG(CASE WHEN symbol = 'DGS10' THEN current_price END) as avg_treasury_10y,
  AVG(CASE WHEN symbol = 'CPIAUCSL' THEN current_price END) as avg_cpi,
  AVG(CASE WHEN symbol = 'CL=F' THEN current_price END) as avg_wti_oil,
  AVG(CASE WHEN symbol = '^VIX' THEN current_price END) as avg_vix,
  AVG(CASE WHEN symbol = '^GSPC' THEN current_price END) as avg_sp500,

  -- Correlation calculations (30-day rolling)
  CORR(
    CASE WHEN asset_symbol LIKE 'XAU%' THEN current_price END,
    CASE WHEN symbol IN ('DX-Y.NYB', 'DTWEXBGS') THEN current_price END
  ) as gold_dxy_correlation,

  COUNT(*) as records
FROM `${project_id}.${dataset_id}.market_context`
WHERE (market_type = 'gold' OR symbol IN ('DX-Y.NYB', 'DTWEXBGS', 'DGS10', 'CPIAUCSL', 'CL=F', '^VIX', '^GSPC'))
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY DATE(timestamp), asset_symbol
ORDER BY date DESC, asset_symbol

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
  COUNT(*) as records
FROM `${project_id}.${dataset_id}.market_context`
WHERE market_type = 'gold'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY DATE(timestamp), asset_symbol
ORDER BY date DESC, asset_symbol

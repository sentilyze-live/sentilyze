SELECT 
  DATE(timestamp) as date,
  asset_symbol,
  AVG(current_price) as avg_price,
  MAX(current_price) as high_price,
  MIN(current_price) as low_price,
  AVG(volatility_index) as avg_volatility,
  AVG(fear_greed_index) as avg_fear_greed,
  AVG(volume_24h) as avg_volume,
  AVG(dominance) as avg_dominance,
  AVG(rsi) as avg_rsi,
  COUNT(*) as records
FROM `${project_id}.${dataset_id}.market_context`
WHERE market_type = 'crypto'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY DATE(timestamp), asset_symbol
ORDER BY date DESC, asset_symbol

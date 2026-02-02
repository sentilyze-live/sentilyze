SELECT 
  market_type,
  asset_symbol,
  DATE(timestamp) as date,
  AVG(sentiment_score) as avg_sentiment,
  STDDEV(sentiment_score) as std_sentiment,
  COUNT(*) as data_points,
  SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) / COUNT(*) * 100 as positive_pct,
  SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) / COUNT(*) * 100 as negative_pct,
  SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) / COUNT(*) * 100 as neutral_pct
FROM `${project_id}.${dataset_id}.sentiment_analysis`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY market_type, asset_symbol, DATE(timestamp)
ORDER BY date DESC, market_type, asset_symbol

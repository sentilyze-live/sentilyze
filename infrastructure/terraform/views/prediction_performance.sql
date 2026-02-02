SELECT 
  p.market_type,
  p.asset_symbol,
  p.model_version,
  COUNT(*) as total_predictions,
  SUM(CASE WHEN pa.direction_correct THEN 1 ELSE 0 END) as correct_predictions,
  SUM(CASE WHEN pa.direction_correct THEN 1 ELSE 0 END) / COUNT(*) * 100 as accuracy_pct,
  AVG(ABS(pa.prediction_error)) as avg_mae,
  AVG(pa.confidence_score) as avg_confidence,
  CORR(pa.confidence_score, CASE WHEN pa.direction_correct THEN 1 ELSE 0 END) as confidence_accuracy_correlation
FROM `${project_id}.${dataset_id}.predictions` p
LEFT JOIN `${project_id}.${dataset_id}.prediction_accuracy` pa 
  ON p.id = pa.prediction_id
WHERE p.validated = TRUE
  AND p.prediction_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY p.market_type, p.asset_symbol, p.model_version
ORDER BY p.market_type, p.asset_symbol, accuracy_pct DESC

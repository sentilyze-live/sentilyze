import { useEffect, useCallback } from 'react';
import { useGoldStore } from '../stores/goldStore';
import { useGoldPrice as useWebSocketGoldPrice } from './useWebSocket';

export function useGoldData(symbol: string = 'XAU/USD') {
  const {
    currentSymbol, price, history, predictions, indicators, sentiment, spikes, correlations,
    isLoadingPrice, isLoadingHistory, isLoadingPredictions, isLoadingIndicators, isLoadingSentiment, isLoadingSpikes, isLoadingCorrelations,
    errorPrice, errorHistory, errorPredictions, errorIndicators, errorSentiment, errorSpikes, errorCorrelations,
    timeframe, setSymbol, setTimeframe, fetchPrice, fetchHistory, fetchPredictions, fetchIndicators, fetchSentiment, fetchSpikes, fetchCorrelations, fetchAll, clearErrors,
  } = useGoldStore();

  useWebSocketGoldPrice(symbol);

  useEffect(() => { setSymbol(symbol); }, [symbol, setSymbol]);

  return {
    currentSymbol, price, history, predictions, indicators, sentiment, spikes, correlations, timeframe,
    isLoading: { price: isLoadingPrice, history: isLoadingHistory, predictions: isLoadingPredictions, indicators: isLoadingIndicators, sentiment: isLoadingSentiment, spikes: isLoadingSpikes, correlations: isLoadingCorrelations },
    error: { price: errorPrice, history: errorHistory, predictions: errorPredictions, indicators: errorIndicators, sentiment: errorSentiment, spikes: errorSpikes, correlations: errorCorrelations },
    refetchAll: useCallback(() => fetchAll(), [fetchAll]),
    refetchPrice: useCallback(() => fetchPrice(), [fetchPrice]),
    refetchHistory: useCallback(() => fetchHistory(), [fetchHistory]),
    refetchPredictions: useCallback(() => fetchPredictions(), [fetchPredictions]),
    refetchIndicators: useCallback(() => fetchIndicators(), [fetchIndicators]),
    refetchSentiment: useCallback(() => fetchSentiment(), [fetchSentiment]),
    refetchSpikes: useCallback(() => fetchSpikes(), [fetchSpikes]),
    refetchCorrelations: useCallback(() => fetchCorrelations(), [fetchCorrelations]),
    changeSymbol: useCallback((newSymbol: string) => setSymbol(newSymbol), [setSymbol]),
    changeTimeframe: useCallback((newTimeframe: string) => setTimeframe(newTimeframe), [setTimeframe]),
    clearErrors,
  };
}

export function useGoldPriceData(symbol: string = 'XAU/USD') {
  const { price, isLoadingPrice, errorPrice, fetchPrice } = useGoldStore();
  useEffect(() => { fetchPrice(); }, [symbol, fetchPrice]);
  return { price, isLoading: isLoadingPrice, error: errorPrice, refetch: fetchPrice };
}

export function useGoldHistory(symbol: string = 'XAU/USD', timeframe: string = '1h') {
  const { history, isLoadingHistory, errorHistory, fetchHistory, timeframe: currentTimeframe } = useGoldStore();
  useEffect(() => { fetchHistory(); }, [symbol, timeframe, fetchHistory]);
  return { history, isLoading: isLoadingHistory, error: errorHistory, timeframe: currentTimeframe, refetch: fetchHistory };
}

export function useGoldPredictions(symbol: string = 'XAU/USD', timeframe: string = '24h') {
  const { predictions, isLoadingPredictions, errorPredictions, fetchPredictions, timeframe: currentTimeframe } = useGoldStore();
  useEffect(() => { fetchPredictions(); }, [symbol, timeframe, fetchPredictions]);
  return { predictions, isLoading: isLoadingPredictions, error: errorPredictions, timeframe: currentTimeframe, refetch: fetchPredictions };
}

export function useTechnicalIndicators(symbol: string = 'XAU/USD') {
  const { indicators, isLoadingIndicators, errorIndicators, fetchIndicators } = useGoldStore();
  useEffect(() => { fetchIndicators(); }, [symbol, fetchIndicators]);
  return { indicators, isLoading: isLoadingIndicators, error: errorIndicators, refetch: fetchIndicators };
}

export function useSentimentData(symbol: string = 'XAU/USD') {
  const { sentiment, isLoadingSentiment, errorSentiment, fetchSentiment } = useGoldStore();
  useEffect(() => { fetchSentiment(); }, [symbol, fetchSentiment]);
  return { sentiment, isLoading: isLoadingSentiment, error: errorSentiment, refetch: fetchSentiment };
}

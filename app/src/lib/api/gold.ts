import api from './client';

// Types - Updated to match backend response format
export interface GoldPrice {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  high24h?: number;
  low24h?: number;
  volume24h?: number;
  timestamp: string;
  source?: string;
}

export interface GoldHistory {
  prices: {
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }[];
}

export interface Prediction {
  price: number;
  changePercent: number;
  direction: 'up' | 'down' | 'neutral';
  modelScore: number;
  sentimentDirection?: 'positive' | 'negative' | 'neutral';
  timeframe?: string;
  confidence?: number;
}

export interface TechnicalIndicators {
  rsi: {
    value: number;
    condition: 'oversold' | 'overbought';
  };
  macd: {
    value: number;
    momentum: 'positive' | 'negative';
    histogram: number;
  };
  bollinger: {
    upper: number;
    middle: number;
    lower: number;
  };
  sma: {
    '20': number;
    '50': number;
    '200': number;
  };
  disclaimer?: string;
}

export interface SentimentData {
  score: number;
  trend: 'positive' | 'neutral' | 'negative';
  keywords: string[];
  newsCount: number;
  socialSentiment: number;
}

export interface SpikeData {
  id: string;
  timestamp: string;
  priceBefore: number;
  priceAfter: number;
  changePercent: number;
  direction: 'up' | 'down';
  severity: 'low' | 'medium' | 'high';
  causes: string[];
}

export interface CorrelationData {
  dxy: {
    correlation: number;
    strength: 'strong' | 'moderate' | 'weak';
  };
  btc: {
    correlation: number;
    strength: 'strong' | 'moderate' | 'weak';
  };
  sp500: {
    correlation: number;
    strength: 'strong' | 'moderate' | 'weak';
  };
}

export interface NewsArticle {
  id: string;
  title: string;
  source: string;
  url: string;
  timestamp: string;
  sentiment: number;
}

export interface NewsResponse {
  articles: NewsArticle[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    hasMore: boolean;
  };
}

// New types for additional endpoints
export interface ScenarioModel {
  model: string;
  prediction: number;
  confidence: number;
  weight: number;
}

export interface ScenarioData {
  symbol: string;
  ensemble_prediction: number;
  ensemble_confidence: number;
  scenarios: {
    '1h': ScenarioModel[];
    '2h': ScenarioModel[];
    '3h': ScenarioModel[];
  };
  timestamp: string;
}

export interface DailyReportData {
  date: string;
  overall_accuracy: number;
  total_predictions: number;
  correct_predictions: number;
  models: {
    model_name: string;
    accuracy: number;
    predictions_count: number;
  }[];
}

export interface MarketContextData {
  symbol: string;
  regime: 'bullish' | 'bearish' | 'neutral';
  trend: {
    direction: 'up' | 'down' | 'sideways';
    strength: number;
  };
  volatility: {
    regime: 'low' | 'normal' | 'high';
    value: number;
  };
  levels: {
    support: number[];
    resistance: number[];
  };
  factors: {
    usd_strength: number;
    interest_rates: number;
    geopolitical_risk: number;
  };
}

export interface CorrelationDetail {
  correlation: number;
  strength: 'strong' | 'moderate' | 'weak';
  direction: 'positive' | 'negative';
  interpretation: string;
}

// API endpoints - Updated to match backend
export const goldApi = {
  getPrice: async (symbol: string = 'XAU/USD'): Promise<GoldPrice> => {
    const response = await api.get('/gold/price/live', {
      params: { symbol }
    });
    return response.data.data;
  },

  getHistory: async (
    symbol: string = 'XAU/USD',
    timeframe: string = '1D',
    limit: number = 100
  ): Promise<GoldHistory> => {
    const response = await api.get('/gold/price/history', {
      params: { symbol, timeframe, limit },
    });
    return response.data.data;
  },

  getPredictions: async (
    symbol: string = 'XAU/USD',
    timeframe: string = '1D'
  ): Promise<{
    predictions: Prediction[];
    timeframes: Record<string, Prediction>;
    disclaimer: string;
    ensemble: Record<string, number>;
  }> => {
    const response = await api.get('/gold/predictions', {
      params: { symbol, timeframe }
    });
    return response.data.data;
  },

  getTechnicalIndicators: async (symbol: string = 'XAU/USD'): Promise<TechnicalIndicators> => {
    const response = await api.get('/gold/technical', {
      params: { symbol }
    });
    return response.data.data;
  },

  getSentiment: async (symbol: string = 'XAU/USD'): Promise<SentimentData> => {
    const response = await api.get('/gold/sentiment', {
      params: { symbol }
    });
    return response.data.data;
  },

  getSpikes: async (
    symbol: string = 'XAU/USD',
    threshold: number = 0.5,
    page: number = 1,
    limit: number = 50
  ): Promise<{ spikes: SpikeData[] }> => {
    const response = await api.get('/gold/spikes', {
      params: { symbol, threshold, page, limit },
    });
    return response.data.data;
  },

  getCorrelations: async (symbol: string = 'XAU/USD'): Promise<CorrelationData> => {
    const response = await api.get('/gold/correlations', {
      params: { symbol }
    });
    return response.data.data;
  },

  getNews: async (
    symbol: string = 'XAU/USD',
    page: number = 1,
    limit: number = 20
  ): Promise<NewsResponse> => {
    const response = await api.get('/gold/news', {
      params: { symbol, page, limit },
    });
    return response.data.data;
  },

  // New endpoints
  getScenarios: async (symbol: string = 'XAUTRY'): Promise<ScenarioData> => {
    const response = await api.get('/gold/scenarios', {
      params: { symbol }
    });
    return response.data;
  },

  getDailyReport: async (): Promise<DailyReportData> => {
    const response = await api.get('/gold/daily-report');
    return response.data;
  },

  getContext: async (symbol: string = 'XAUUSD'): Promise<MarketContextData> => {
    const response = await api.get(`/gold/context/${symbol}`);
    return response.data;
  },

  getCorrelation: async (
    symbol: string = 'XAUUSD',
    compareWith: string[] = ['DXY', 'SPX', 'US10Y'],
    days: number = 30
  ): Promise<Record<string, CorrelationDetail>> => {
    const response = await api.get(`/gold/correlation/${symbol}`, {
      params: {
        compare_with: compareWith.join(','),
        days
      }
    });
    return response.data;
  },
};

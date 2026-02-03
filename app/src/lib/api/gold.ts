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
  direction: 'up' | 'down';
  modelScore: number;
  sentimentDirection: 'positive' | 'negative' | 'neutral';
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

// API endpoints - Updated to match backend
export const goldApi = {
  getPrice: async (): Promise<GoldPrice> => {
    const response = await api.get('/gold/price/live');
    return response.data.data;
  },

  getHistory: async (
    timeframe: string = '1D',
    limit: number = 100
  ): Promise<GoldHistory> => {
    const response = await api.get('/gold/price/history', {
      params: { timeframe, limit },
    });
    return response.data.data;
  },

  getPredictions: async (): Promise<{
    timeframes: Record<string, Prediction>;
    disclaimer: string;
    ensemble: Record<string, number>;
  }> => {
    const response = await api.get('/gold/predictions');
    return response.data.data;
  },

  getTechnicalIndicators: async (): Promise<TechnicalIndicators> => {
    const response = await api.get('/gold/technical');
    return response.data.data;
  },

  getSentiment: async (): Promise<SentimentData> => {
    const response = await api.get('/gold/sentiment');
    return response.data.data;
  },

  getSpikes: async (
    page: number = 1,
    limit: number = 50
  ): Promise<{ spikes: SpikeData[] }> => {
    const response = await api.get('/gold/spikes', {
      params: { page, limit },
    });
    return response.data.data;
  },

  getCorrelations: async (): Promise<CorrelationData> => {
    const response = await api.get('/gold/correlations');
    return response.data.data;
  },

  getNews: async (
    page: number = 1,
    limit: number = 20
  ): Promise<NewsResponse> => {
    const response = await api.get('/gold/news', {
      params: { page, limit },
    });
    return response.data.data;
  },
};

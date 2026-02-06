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

// Normalize symbol for path params (XAU/USD -> XAUUSD)
const normalizeSymbol = (symbol: string): string =>
  symbol.replace('/', '');

// API endpoints - Updated to match actual backend routes
export const goldApi = {
  getPrice: async (symbol: string = 'XAU/USD'): Promise<GoldPrice> => {
    // Backend /gold/prices returns all prices, extract the one we need
    const response = await api.get('/gold/prices');
    const prices = response.data?.data?.prices || response.data?.prices || [];
    const sym = normalizeSymbol(symbol);
    const match = prices.find((p: { symbol: string }) => p.symbol === sym || p.symbol === symbol);

    if (match) {
      return {
        symbol: match.symbol,
        price: match.price,
        change: match.change || 0,
        changePercent: match.change_percent || 0,
        timestamp: match.timestamp,
      };
    }

    // Fallback: try direct endpoint
    const directResponse = await api.get(`/gold/price/${sym}`);
    const data = directResponse.data?.data || directResponse.data;
    return {
      symbol: data.symbol || sym,
      price: data.price,
      change: data.change || 0,
      changePercent: data.changePercent || data.change_percent || 0,
      high24h: data.highPrice || data.high24h || data.high_price || 0,
      low24h: data.lowPrice || data.low24h || data.low_price || 0,
      timestamp: data.timestamp || new Date().toISOString(),
    };
  },

  getHistory: async (
    symbol: string = 'XAU/USD',
    timeframe: string = '1D',
    limit: number = 100
  ): Promise<GoldHistory> => {
    try {
      const sym = normalizeSymbol(symbol);
      const response = await api.get(`/gold/history/${sym}`, {
        params: { timeframe, limit },
      });
      const data = response.data?.data || response.data;
      return { prices: data?.prices || [] };
    } catch {
      return { prices: [] };
    }
  },

  getPredictions: async (
    symbol: string = 'XAU/USD',
    _timeframe: string = '1D'
  ): Promise<{
    predictions: Prediction[];
    timeframes: Record<string, Prediction>;
    disclaimer: string;
    ensemble: Record<string, number>;
  }> => {
    const sym = normalizeSymbol(symbol);
    const response = await api.get(`/gold/predictions/${sym}`);
    const data = response.data?.data || response.data;

    // Normalize response to expected format
    if (Array.isArray(data)) {
      const predictions: Prediction[] = data.map((item: { price: number; changePercent: number; direction: string; confidence: number; timeframe: string }) => ({
        price: item.price,
        changePercent: item.changePercent || item.change_percent || 0,
        direction: item.direction as 'up' | 'down' | 'neutral',
        modelScore: item.confidence || item.confidenceScore || 0,
        timeframe: item.timeframe,
        confidence: item.confidence || item.confidenceScore || 0,
      }));
      return {
        predictions,
        timeframes: {},
        disclaimer: 'Model çıktısıdır, yatırım tavsiyesi niteliği taşımaz.',
        ensemble: {},
      };
    }

    return data;
  },

  getTechnicalIndicators: async (symbol: string = 'XAU/USD'): Promise<TechnicalIndicators> => {
    try {
      const sym = normalizeSymbol(symbol);
      const response = await api.get(`/gold/technical-indicators/${sym}`);
      const data = response.data?.data || response.data;
      return {
        rsi: data.rsi || { value: 0, condition: 'oversold' },
        macd: data.macd || { value: 0, momentum: 'positive', histogram: 0 },
        bollinger: data.bollinger || { upper: 0, middle: 0, lower: 0 },
        sma: data.sma || { '20': 0, '50': 0, '200': 0 },
      };
    } catch {
      return {
        rsi: { value: 0, condition: 'oversold' },
        macd: { value: 0, momentum: 'positive', histogram: 0 },
        bollinger: { upper: 0, middle: 0, lower: 0 },
        sma: { '20': 0, '50': 0, '200': 0 },
        disclaimer: 'Teknik analiz verisi alınamadı',
      };
    }
  },

  getSentiment: async (symbol: string = 'XAU/USD'): Promise<SentimentData> => {
    try {
      const sym = normalizeSymbol(symbol);
      const response = await api.get(`/gold/sentiment/${sym}`);
      const data = response.data;
      // Backend returns { aggregate: { score, label, confidence, sentiment_count }, sources: {...} }
      const aggregate = data?.aggregate || data?.data?.aggregate || {};
      const sources = data?.sources || data?.data?.sources || {};
      const totalMentions = Object.values(sources).reduce(
        (sum: number, s: unknown) => sum + ((s as { mentions?: number })?.mentions || 0),
        0
      );
      const socialSource = sources?.social_media || sources?.twitter || {};
      return {
        score: aggregate.score ?? data?.score ?? 0,
        trend: (aggregate.label as SentimentData['trend']) || data?.trend || 'neutral',
        keywords: data?.keywords || [],
        newsCount: aggregate.sentiment_count || totalMentions || 0,
        socialSentiment: (socialSource as { sentiment?: number })?.sentiment || 0,
      };
    } catch {
      // Fallback if endpoint is temporarily unavailable
      return {
        score: 0.5,
        trend: 'neutral',
        keywords: [],
        newsCount: 0,
        socialSentiment: 0,
      };
    }
  },

  getSpikes: async (
    _symbol: string = 'XAU/USD',
    _threshold: number = 0.5,
    _page: number = 1,
    _limit: number = 50
  ): Promise<{ spikes: SpikeData[] }> => {
    // Backend doesn't have a spikes endpoint
    return { spikes: [] };
  },

  getCorrelations: async (symbol: string = 'XAU/USD'): Promise<CorrelationData> => {
    const sym = normalizeSymbol(symbol);
    const assets = ['DXY', 'BTC', 'SPX'];
    const result: CorrelationData = {
      dxy: { correlation: 0, strength: 'weak' },
      btc: { correlation: 0, strength: 'weak' },
      sp500: { correlation: 0, strength: 'weak' },
    };

    try {
      const responses = await Promise.allSettled(
        assets.map(asset =>
          api.get(`/gold/correlation/${sym}`, { params: { compare_with: asset, days: 30 } })
        )
      );

      const keys: (keyof CorrelationData)[] = ['dxy', 'btc', 'sp500'];
      responses.forEach((resp, i) => {
        if (resp.status === 'fulfilled') {
          const data = resp.value.data?.data || resp.value.data;
          result[keys[i]] = {
            correlation: data.correlation || 0,
            strength: (data.strength?.toLowerCase() === 'strong' ? 'strong'
              : data.strength?.toLowerCase() === 'moderate' ? 'moderate' : 'weak') as 'strong' | 'moderate' | 'weak',
          };
        }
      });
    } catch {
      // Return defaults on error
    }
    return result;
  },

  getNews: async (
    _symbol: string = 'XAU/USD',
    page: number = 1,
    limit: number = 20
  ): Promise<NewsResponse> => {
    try {
      const response = await api.get('/gold/news', { params: { page, limit } });
      const data = response.data?.data || response.data;
      const articles = (data?.articles || []).map((a: { id: string; title: string; source: string; url: string; timestamp: string; sentiment: number }) => ({
        id: a.id,
        title: a.title,
        source: a.source,
        url: a.url,
        timestamp: a.timestamp,
        sentiment: a.sentiment || 0,
      }));
      const pagination = data?.pagination || {};
      return {
        articles,
        pagination: {
          page: pagination.page || page,
          limit: pagination.limit || limit,
          total: pagination.total || 0,
          hasMore: pagination.has_more || false,
        },
      };
    } catch {
      return { articles: [], pagination: { page, limit, total: 0, hasMore: false } };
    }
  },

  getScenarios: async (_symbol: string = 'XAUUSD'): Promise<ScenarioData> => {
    const response = await api.get('/gold/scenarios');
    const data = response.data;

    // Backend returns array of scenarios, transform to expected format
    if (Array.isArray(data)) {
      const scenarios: Record<string, ScenarioModel[]> = { '1h': [], '2h': [], '3h': [] };
      let totalPrediction = 0;
      let totalConfidence = 0;
      let count = 0;

      data.forEach((item: { timeframe: string; price: number; confidenceScore: number; models: ScenarioModel[] }) => {
        const tf = item.timeframe?.replace(' Saat', 'h').replace(' ', '') || '';
        const key = tf === '1h' || tf === '1Saat' ? '1h' : tf === '2h' || tf === '2Saat' ? '2h' : '3h';
        scenarios[key] = (item.models || []).map((m: ScenarioModel & { name?: string }) => ({
          model: m.model || m.name || 'Unknown',
          prediction: m.prediction || 0,
          confidence: m.confidence || 0,
          weight: m.weight || 0,
        }));
        totalPrediction += item.price || 0;
        totalConfidence += item.confidenceScore || 0;
        count++;
      });

      return {
        symbol: 'XAUUSD',
        ensemble_prediction: count > 0 ? totalPrediction / count : 0,
        ensemble_confidence: count > 0 ? (totalConfidence / count) / 100 : 0,
        scenarios: scenarios as ScenarioData['scenarios'],
        timestamp: new Date().toISOString(),
      };
    }

    return data;
  },

  getDailyReport: async (): Promise<DailyReportData> => {
    const response = await api.get('/gold/daily-report');
    const data = response.data;
    return {
      date: data.date,
      overall_accuracy: data.accuracy ? data.accuracy / 100 : data.overall_accuracy || 0,
      total_predictions: data.totalPredictions || data.total_predictions || 0,
      correct_predictions: data.correctPredictions || data.correct_predictions || 0,
      models: (data.modelPerformance || data.models || []).map((m: { model: string; model_name: string; accuracy: number; weight: number; predictions_count: number }) => ({
        model_name: m.model || m.model_name,
        accuracy: m.accuracy > 1 ? m.accuracy / 100 : m.accuracy,
        predictions_count: m.predictions_count || Math.round((data.totalPredictions || 24) * (m.weight || 0.33)),
      })),
    };
  },

  getContext: async (symbol: string = 'XAUUSD'): Promise<MarketContextData> => {
    const sym = normalizeSymbol(symbol);
    const response = await api.get(`/gold/context/${sym}`);
    const raw = response.data?.data || response.data;
    return {
      symbol: raw.symbol || sym,
      regime: raw.regime || 'neutral',
      trend: {
        direction: raw.trend_direction || raw.trend?.direction || 'sideways',
        strength: raw.trend_strength || raw.trend?.strength || 0.5,
      },
      volatility: {
        regime: raw.volatility_regime || raw.volatility?.regime || 'normal',
        value: raw.volatility_value || raw.volatility?.value || 0.5,
      },
      levels: {
        support: raw.technical_levels?.support
          ? (Array.isArray(raw.technical_levels.support) ? raw.technical_levels.support : [raw.technical_levels.support])
          : raw.levels?.support || [],
        resistance: raw.technical_levels?.resistance
          ? (Array.isArray(raw.technical_levels.resistance) ? raw.technical_levels.resistance : [raw.technical_levels.resistance])
          : raw.levels?.resistance || [],
      },
      factors: {
        usd_strength: raw.factors?.usd_strength || 0,
        interest_rates: raw.factors?.interest_rates || 0,
        geopolitical_risk: raw.factors?.geopolitical_risk || 0,
      },
    };
  },

  getCorrelation: async (
    symbol: string = 'XAUUSD',
    compareWith: string[] = ['DXY', 'SPX', 'US10Y'],
    days: number = 30
  ): Promise<Record<string, CorrelationDetail>> => {
    const sym = normalizeSymbol(symbol);
    const response = await api.get(`/gold/correlation/${sym}`, {
      params: {
        compare_with: compareWith.join(','),
        days,
      },
    });
    const raw = response.data?.data || response.data;

    // Backend returns a single correlation result, transform to record format
    if (raw.correlation !== undefined && raw.strength !== undefined) {
      const result: Record<string, CorrelationDetail> = {};
      compareWith.forEach((asset) => {
        result[asset] = {
          correlation: raw.correlation,
          strength: raw.strength?.toLowerCase() === 'strong' ? 'strong'
            : raw.strength?.toLowerCase() === 'moderate' ? 'moderate' : 'weak',
          direction: raw.direction || (raw.correlation >= 0 ? 'positive' : 'negative'),
          interpretation: raw.interpretation || `${asset} ile ${raw.strength} korelasyon`,
        };
      });
      return result;
    }

    return raw;
  },
};

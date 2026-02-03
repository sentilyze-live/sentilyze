import api from './client';

// Types
export interface DashboardSummary {
  lastUpdated: string;
  markets: {
    symbol: string;
    name: string;
    price: number;
    change: number;
    changePercent: number;
    trend: 'up' | 'down' | 'neutral';
  }[];
  summary: {
    totalSymbols: number;
    activePredictions: number;
    avgSentiment: number;
    alertsCount: number;
  };
}

export interface ShortPrediction {
  symbol: string;
  direction: 'up' | 'down' | 'neutral';
  confidence: number;
  timeframe: string;
  keyFactors: string[];
}

export interface StatsData {
  totalUsers: number;
  activeUsers: number;
  totalRequests: number;
  requestsToday: number;
  avgResponseTime: number;
  uptime: number;
  errors: {
    count: number;
    lastError: string;
  };
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  services: {
    name: string;
    status: 'healthy' | 'degraded' | 'unhealthy';
    latency: number;
  }[];
  lastChecked: string;
}

// API endpoints
export const publicApi = {
  getSummary: async (): Promise<DashboardSummary> => {
    const response = await api.get('/public/summary');
    return response.data;
  },

  getShortPredictions: async (): Promise<ShortPrediction[]> => {
    const response = await api.get('/public/predictions');
    return response.data;
  },

  getStats: async (): Promise<StatsData> => {
    const response = await api.get('/public/stats');
    return response.data;
  },

  getHealth: async (): Promise<HealthStatus> => {
    const response = await api.get('/public/health');
    return response.data;
  },

  getSymbols: async (): Promise<{ symbol: string; name: string; type: string }[]> => {
    const response = await api.get('/public/symbols');
    return response.data;
  },

  getTimeframes: async (): Promise<string[]> => {
    const response = await api.get('/public/timeframes');
    return response.data;
  },

  contact: async (data: {
    name: string;
    email: string;
    subject: string;
    message: string;
  }): Promise<void> => {
    await api.post('/public/contact', data);
  },

  subscribe: async (email: string): Promise<void> => {
    await api.post('/public/subscribe', { email });
  },
};

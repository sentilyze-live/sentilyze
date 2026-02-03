import axios from 'axios';

const FINNHUB_API_BASE = 'https://finnhub.io/api/v1';
const FINNHUB_API_KEY = import.meta.env.VITE_FINNHUB_API_KEY || 'cufe5f9r01qhcm6a4jr0cufe5f9r01qhcm6a4jrg';

export interface FinnhubQuote {
  c: number;  // Current price
  d: number;  // Change
  dp: number; // Percent change
  h: number;  // High price of the day
  l: number;  // Low price of the day
  o: number;  // Open price of the day
  pc: number; // Previous close price
  t: number;  // Timestamp
}

export interface ForexRate {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  high: number;
  low: number;
  timestamp: number;
}

// Named export for backwards compatibility
export type { ForexRate as default };

// Get real-time forex rates
export const getForexRate = async (symbol: string): Promise<ForexRate | null> => {
  try {
    const response = await axios.get<FinnhubQuote>(
      `${FINNHUB_API_BASE}/quote`,
      {
        params: {
          symbol: `OANDA:${symbol}`,
          token: FINNHUB_API_KEY,
        },
        timeout: 10000,
      }
    );

    const data = response.data;

    // Finnhub bazen 0 değerleri dönebilir, bu durumda null döndür
    if (data.c === 0 || !data.c) {
      return null;
    }

    return {
      symbol,
      name: symbol,
      price: data.c,
      change: data.d,
      changePercent: data.dp,
      high: data.h,
      low: data.l,
      timestamp: data.t,
    };
  } catch (error) {
    console.error(`Finnhub error for ${symbol}:`, error);
    return null;
  }
};

// Get XAU/USD (Gold) price
export const getGoldPrice = async (): Promise<ForexRate | null> => {
  return getForexRate('XAU_USD');
};

// Get USD/TRY price
export const getUSDTRY = async (): Promise<ForexRate | null> => {
  return getForexRate('USD_TRY');
};

// Get EUR/TRY price
export const getEURTRY = async (): Promise<ForexRate | null> => {
  return getForexRate('EUR_TRY');
};

// Get EUR/USD price
export const getEURUSD = async (): Promise<ForexRate | null> => {
  return getForexRate('EUR_USD');
};

// Get all prices in one call
export const getAllPrices = async () => {
  try {
    const [gold, usdtry, eurtry] = await Promise.all([
      getGoldPrice(),
      getUSDTRY(),
      getEURTRY(),
    ]);

    return {
      gold,
      usdtry,
      eurtry,
    };
  } catch (error) {
    console.error('Error fetching all prices:', error);
    return {
      gold: null,
      usdtry: null,
      eurtry: null,
    };
  }
};

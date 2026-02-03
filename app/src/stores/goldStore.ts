import { create } from 'zustand';
import { goldApi, type GoldPrice, type GoldHistory, type Prediction, type TechnicalIndicator, type SentimentData, type SpikeAnalysis, type Correlation } from '../lib/api/gold';

interface GoldState {
  // Data
  currentSymbol: string;
  price: GoldPrice | null;
  history: GoldHistory | null;
  predictions: Prediction[];
  indicators: TechnicalIndicator[];
  sentiment: SentimentData | null;
  spikes: SpikeAnalysis | null;
  correlations: Correlation[];

  // Loading states
  isLoadingPrice: boolean;
  isLoadingHistory: boolean;
  isLoadingPredictions: boolean;
  isLoadingIndicators: boolean;
  isLoadingSentiment: boolean;
  isLoadingSpikes: boolean;
  isLoadingCorrelations: boolean;

  // Errors
  errorPrice: string | null;
  errorHistory: string | null;
  errorPredictions: string | null;
  errorIndicators: string | null;
  errorSentiment: string | null;
  errorSpikes: string | null;
  errorCorrelations: string | null;

  // Timeframe
  timeframe: string;

  // Actions
  setSymbol: (symbol: string) => void;
  setTimeframe: (timeframe: string) => void;
  fetchPrice: () => Promise<void>;
  fetchHistory: () => Promise<void>;
  fetchPredictions: () => Promise<void>;
  fetchIndicators: () => Promise<void>;
  fetchSentiment: () => Promise<void>;
  fetchSpikes: (threshold?: number) => Promise<void>;
  fetchCorrelations: () => Promise<void>;
  fetchAll: () => Promise<void>;
  updatePrice: (price: GoldPrice) => void;
  clearErrors: () => void;
}

export const useGoldStore = create<GoldState>((set, get) => ({
  currentSymbol: 'XAU/USD',
  price: null,
  history: null,
  predictions: [],
  indicators: [],
  sentiment: null,
  spikes: null,
  correlations: [],

  isLoadingPrice: false,
  isLoadingHistory: false,
  isLoadingPredictions: false,
  isLoadingIndicators: false,
  isLoadingSentiment: false,
  isLoadingSpikes: false,
  isLoadingCorrelations: false,

  errorPrice: null,
  errorHistory: null,
  errorPredictions: null,
  errorIndicators: null,
  errorSentiment: null,
  errorSpikes: null,
  errorCorrelations: null,

  timeframe: '1h',

  setSymbol: (symbol) => {
    set({ currentSymbol: symbol });
    get().fetchAll();
  },

  setTimeframe: (timeframe) => {
    set({ timeframe });
    get().fetchHistory();
    get().fetchPredictions();
  },

  fetchPrice: async () => {
    const { currentSymbol } = get();
    set({ isLoadingPrice: true, errorPrice: null });
    try {
      const price = await goldApi.getPrice(currentSymbol);
      set({ price, isLoadingPrice: false });
    } catch (error) {
      set({
        errorPrice: error instanceof Error ? error.message : 'Fiyat alınamadı',
        isLoadingPrice: false,
      });
    }
  },

  fetchHistory: async () => {
    const { currentSymbol, timeframe } = get();
    set({ isLoadingHistory: true, errorHistory: null });
    try {
      const history = await goldApi.getHistory(currentSymbol, timeframe);
      set({ history, isLoadingHistory: false });
    } catch (error) {
      set({
        errorHistory: error instanceof Error ? error.message : 'Geçmiş veri alınamadı',
        isLoadingHistory: false,
      });
    }
  },

  fetchPredictions: async () => {
    const { currentSymbol, timeframe } = get();
    set({ isLoadingPredictions: true, errorPredictions: null });
    try {
      const predictions = await goldApi.getPredictions(currentSymbol, timeframe);
      set({ predictions, isLoadingPredictions: false });
    } catch (error) {
      set({
        errorPredictions: error instanceof Error ? error.message : 'Tahminler alınamadı',
        isLoadingPredictions: false,
      });
    }
  },

  fetchIndicators: async () => {
    const { currentSymbol } = get();
    set({ isLoadingIndicators: true, errorIndicators: null });
    try {
      const indicators = await goldApi.getTechnicalIndicators(currentSymbol);
      set({ indicators, isLoadingIndicators: false });
    } catch (error) {
      set({
        errorIndicators: error instanceof Error ? error.message : 'Göstergeler alınamadı',
        isLoadingIndicators: false,
      });
    }
  },

  fetchSentiment: async () => {
    const { currentSymbol } = get();
    set({ isLoadingSentiment: true, errorSentiment: null });
    try {
      const sentiment = await goldApi.getSentiment(currentSymbol);
      set({ sentiment, isLoadingSentiment: false });
    } catch (error) {
      set({
        errorSentiment: error instanceof Error ? error.message : 'Duygu analizi alınamadı',
        isLoadingSentiment: false,
      });
    }
  },

  fetchSpikes: async (threshold = 0.5) => {
    const { currentSymbol } = get();
    set({ isLoadingSpikes: true, errorSpikes: null });
    try {
      const spikes = await goldApi.getSpikes(currentSymbol, threshold);
      set({ spikes, isLoadingSpikes: false });
    } catch (error) {
      set({
        errorSpikes: error instanceof Error ? error.message : 'Spike analizi alınamadı',
        isLoadingSpikes: false,
      });
    }
  },

  fetchCorrelations: async () => {
    const { currentSymbol } = get();
    set({ isLoadingCorrelations: true, errorCorrelations: null });
    try {
      const correlations = await goldApi.getCorrelations(currentSymbol);
      set({ correlations, isLoadingCorrelations: false });
    } catch (error) {
      set({
        errorCorrelations: error instanceof Error ? error.message : 'Korelasyonlar alınamadı',
        isLoadingCorrelations: false,
      });
    }
  },

  fetchAll: async () => {
    await Promise.all([
      get().fetchPrice(),
      get().fetchHistory(),
      get().fetchPredictions(),
      get().fetchIndicators(),
      get().fetchSentiment(),
      get().fetchSpikes(),
      get().fetchCorrelations(),
    ]);
  },

  updatePrice: (price) => set({ price }),

  clearErrors: () =>
    set({
      errorPrice: null,
      errorHistory: null,
      errorPredictions: null,
      errorIndicators: null,
      errorSentiment: null,
      errorSpikes: null,
      errorCorrelations: null,
    }),
}));

// Selectors
export const useCurrentPrice = () => useGoldStore((state) => state.price);
export const useGoldHistory = () => useGoldStore((state) => state.history);
export const usePredictions = () => useGoldStore((state) => state.predictions);
export const useTechnicalIndicators = () => useGoldStore((state) => state.indicators);
export const useSentiment = () => useGoldStore((state) => state.sentiment);
export const useSpikes = () => useGoldStore((state) => state.spikes);
export const useCorrelations = () => useGoldStore((state) => state.correlations);
export const useGoldLoading = () => useGoldStore((state) => ({
  price: state.isLoadingPrice,
  history: state.isLoadingHistory,
  predictions: state.isLoadingPredictions,
  indicators: state.isLoadingIndicators,
  sentiment: state.isLoadingSentiment,
  spikes: state.isLoadingSpikes,
  correlations: state.isLoadingCorrelations,
}));

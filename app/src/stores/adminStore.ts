import { create } from 'zustand';
import { adminApi, type Service, type LogEntry, type Alert, type PubSubMetrics } from '../lib/api/admin';

interface AdminState {
  services: Service[];
  logs: LogEntry[];
  alerts: Alert[];
  pubsubMetrics: PubSubMetrics[];

  isLoadingServices: boolean;
  isLoadingLogs: boolean;
  isLoadingAlerts: boolean;
  isLoadingMetrics: boolean;

  errorServices: string | null;
  errorLogs: string | null;
  errorAlerts: string | null;
  errorMetrics: string | null;

  logFilter: {
    level: string | null;
    service: string | null;
    search: string;
  };
  alertFilter: {
    type: string | null;
    acknowledged: boolean | null;
  };

  fetchServices: () => Promise<void>;
  fetchLogs: (limit?: number, offset?: number) => Promise<void>;
  fetchAlerts: () => Promise<void>;
  fetchMetrics: () => Promise<void>;
  restartService: (serviceId: string) => Promise<void>;
  scaleService: (serviceId: string, replicas: number) => Promise<void>;
  deployService: (serviceId: string) => Promise<void>;
  acknowledgeAlert: (alertId: string) => Promise<void>;
  resolveAlert: (alertId: string) => Promise<void>;
  createAlert: (alert: Omit<Alert, 'id' | 'createdAt' | 'acknowledged' | 'resolved'>) => Promise<void>;
  clearLogs: () => void;
  setLogFilter: (filter: Partial<AdminState['logFilter']>) => void;
  setAlertFilter: (filter: Partial<AdminState['alertFilter']>) => void;
  clearErrors: () => void;
}

export const useAdminStore = create<AdminState>((set, get) => ({
  services: [],
  logs: [],
  alerts: [],
  pubsubMetrics: [],

  isLoadingServices: false,
  isLoadingLogs: false,
  isLoadingAlerts: false,
  isLoadingMetrics: false,

  errorServices: null,
  errorLogs: null,
  errorAlerts: null,
  errorMetrics: null,

  logFilter: { level: null, service: null, search: '' },
  alertFilter: { type: null, acknowledged: null },

  fetchServices: async () => {
    set({ isLoadingServices: true, errorServices: null });
    try {
      const services = await adminApi.getServices();
      set({ services, isLoadingServices: false });
    } catch (error) {
      set({ errorServices: error instanceof Error ? error.message : 'Servisler alınamadı', isLoadingServices: false });
    }
  },

  fetchLogs: async (limit = 100, offset = 0) => {
    set({ isLoadingLogs: true, errorLogs: null });
    try {
      const logs = await adminApi.getLogs(undefined, undefined, limit, offset);
      set({ logs, isLoadingLogs: false });
    } catch (error) {
      set({ errorLogs: error instanceof Error ? error.message : 'Loglar alınamadı', isLoadingLogs: false });
    }
  },

  fetchAlerts: async () => {
    set({ isLoadingAlerts: true, errorAlerts: null });
    try {
      const alerts = await adminApi.getAlerts();
      set({ alerts, isLoadingAlerts: false });
    } catch (error) {
      set({ errorAlerts: error instanceof Error ? error.message : 'Uyarılar alınamadı', isLoadingAlerts: false });
    }
  },

  fetchMetrics: async () => {
    set({ isLoadingMetrics: true, errorMetrics: null });
    try {
      const metrics = await adminApi.getPubSubMetrics();
      set({ pubsubMetrics: metrics, isLoadingMetrics: false });
    } catch (error) {
      set({ errorMetrics: error instanceof Error ? error.message : 'Metrikler alınamadı', isLoadingMetrics: false });
    }
  },

  restartService: async (serviceId: string) => {
    try {
      await adminApi.restartService(serviceId);
      get().fetchServices();
    } catch (error) { throw error; }
  },

  scaleService: async (serviceId: string, replicas: number) => {
    try {
      await adminApi.scaleService(serviceId, replicas);
      get().fetchServices();
    } catch (error) { throw error; }
  },

  deployService: async (serviceId: string) => {
    try {
      await adminApi.deployService(serviceId);
      get().fetchServices();
    } catch (error) { throw error; }
  },

  acknowledgeAlert: async (alertId: string) => {
    try {
      await adminApi.acknowledgeAlert(alertId);
      get().fetchAlerts();
    } catch (error) { throw error; }
  },

  resolveAlert: async (alertId: string) => {
    try {
      await adminApi.resolveAlert(alertId);
      get().fetchAlerts();
    } catch (error) { throw error; }
  },

  createAlert: async (alert) => {
    try {
      await adminApi.createAlert(alert);
      get().fetchAlerts();
    } catch (error) { throw error; }
  },

  clearLogs: () => set({ logs: [] }),

  setLogFilter: (filter) => set((state) => ({ logFilter: { ...state.logFilter, ...filter } })),
  setAlertFilter: (filter) => set((state) => ({ alertFilter: { ...state.alertFilter, ...filter } })),

  clearErrors: () => set({ errorServices: null, errorLogs: null, errorAlerts: null, errorMetrics: null }),
}));

export const useServices = () => useAdminStore((state) => state.services);
export const useLogs = () => useAdminStore((state) => state.logs);
export const useAlerts = () => useAdminStore((state) => state.alerts);
export const usePubSubMetrics = () => useAdminStore((state) => state.pubsubMetrics);
export const useAdminLoading = () => useAdminStore((state) => ({
  services: state.isLoadingServices,
  logs: state.isLoadingLogs,
  alerts: state.isLoadingAlerts,
  metrics: state.isLoadingMetrics,
}));

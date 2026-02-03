import { useEffect, useCallback } from 'react';
import { useAdminStore } from '../stores/adminStore';
import { useAlerts as useWebSocketAlerts } from './useWebSocket';

export function useAdminData() {
  const {
    services, logs, alerts, pubsubMetrics,
    isLoadingServices, isLoadingLogs, isLoadingAlerts, isLoadingMetrics,
    errorServices, errorLogs, errorAlerts, errorMetrics,
    logFilter, alertFilter,
    fetchServices, fetchLogs, fetchAlerts, fetchMetrics,
    restartService, scaleService, deployService,
    acknowledgeAlert, resolveAlert, createAlert,
    clearLogs, setLogFilter, setAlertFilter, clearErrors,
  } = useAdminStore();

  const wsAlerts = useWebSocketAlerts();

  useEffect(() => {
    fetchServices();
    fetchLogs();
    fetchAlerts();
    fetchMetrics();
  }, [fetchServices, fetchLogs, fetchAlerts, fetchMetrics]);

  return {
    services, logs, alerts: [...alerts, ...(wsAlerts as never[])], pubsubMetrics,
    isLoading: { services: isLoadingServices, logs: isLoadingLogs, alerts: isLoadingAlerts, metrics: isLoadingMetrics },
    error: { services: errorServices, logs: errorLogs, alerts: errorAlerts, metrics: errorMetrics },
    filters: { logFilter, alertFilter },
    refetchAll: useCallback(() => { fetchServices(); fetchLogs(); fetchAlerts(); fetchMetrics(); }, [fetchServices, fetchLogs, fetchAlerts, fetchMetrics]),
    fetchServices, fetchLogs, fetchAlerts, fetchMetrics,
    restartService: useCallback((id: string) => restartService(id), [restartService]),
    scaleService: useCallback((id: string, replicas: number) => scaleService(id, replicas), [scaleService]),
    deployService: useCallback((id: string) => deployService(id), [deployService]),
    acknowledgeAlert: useCallback((id: string) => acknowledgeAlert(id), [acknowledgeAlert]),
    resolveAlert: useCallback((id: string) => resolveAlert(id), [resolveAlert]),
    createAlert: useCallback((alert: unknown) => createAlert(alert as Parameters<typeof createAlert>[0]), [createAlert]),
    clearLogs, setLogFilter, setAlertFilter, clearErrors,
  };
}

export function useServices() {
  const { services, isLoadingServices, errorServices, fetchServices, restartService, scaleService, deployService } = useAdminStore();
  useEffect(() => { fetchServices(); }, [fetchServices]);
  return { services, isLoading: isLoadingServices, error: errorServices, refetch: fetchServices, restartService, scaleService, deployService };
}

export function useLogs(serviceId?: string) {
  const { logs, isLoadingLogs, errorLogs, fetchLogs, clearLogs, setLogFilter, logFilter } = useAdminStore();
  useEffect(() => { fetchLogs(); }, [fetchLogs]);
  return { logs, isLoading: isLoadingLogs, error: errorLogs, refetch: fetchLogs, clearLogs, setLogFilter, filter: logFilter };
}

export function useAlerts() {
  const { alerts, isLoadingAlerts, errorAlerts, fetchAlerts, acknowledgeAlert, resolveAlert, alertFilter, setAlertFilter } = useAdminStore();
  useEffect(() => { fetchAlerts(); }, [fetchAlerts]);
  return { alerts, isLoading: isLoadingAlerts, error: errorAlerts, refetch: fetchAlerts, acknowledgeAlert, resolveAlert, filter: alertFilter, setFilter: setAlertFilter };
}

export function usePubSubMetrics() {
  const { pubsubMetrics, isLoadingMetrics, errorMetrics, fetchMetrics } = useAdminStore();
  useEffect(() => { fetchMetrics(); }, [fetchMetrics]);
  return { metrics: pubsubMetrics, isLoading: isLoadingMetrics, error: errorMetrics, refetch: fetchMetrics };
}

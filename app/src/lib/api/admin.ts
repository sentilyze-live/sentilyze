import api from './client';

// Types
export interface Service {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'error' | 'deploying';
  replicas: number;
  cpu: number;
  memory: number;
  uptime: string;
  lastDeployment: string;
  region: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  service: string;
  message: string;
  metadata?: Record<string, unknown>;
}

export interface Alert {
  id: string;
  type: 'error' | 'warning' | 'info';
  title: string;
  message: string;
  service?: string;
  createdAt: string;
  acknowledged: boolean;
  resolved: boolean;
}

export interface PubSubMetrics {
  topic: string;
  subscription: string;
  messagesPublished: number;
  messagesAcked: number;
  messagesFailed: number;
  oldestUnackedMessageAge: string;
  deadLetterMessageCount: number;
}

// Admin API endpoints
export const adminApi = {
  // Services
  getServices: async (): Promise<Service[]> => {
    const response = await api.get('/admin/services');
    return response.data;
  },

  getService: async (serviceId: string): Promise<Service> => {
    const response = await api.get(`/admin/services/${serviceId}`);
    return response.data;
  },

  restartService: async (serviceId: string): Promise<void> => {
    await api.post(`/admin/services/${serviceId}/restart`);
  },

  scaleService: async (serviceId: string, replicas: number): Promise<void> => {
    await api.post(`/admin/services/${serviceId}/scale`, { replicas });
  },

  deployService: async (serviceId: string): Promise<void> => {
    await api.post(`/admin/services/${serviceId}/deploy`);
  },

  // Logs
  getLogs: async (
    serviceId?: string,
    level?: string,
    limit: number = 100,
    offset: number = 0
  ): Promise<LogEntry[]> => {
    const response = await api.get('/admin/logs', {
      params: { serviceId, level, limit, offset },
    });
    return response.data;
  },

  clearLogs: async (serviceId?: string): Promise<void> => {
    await api.delete('/admin/logs', { params: { serviceId } });
  },

  // Alerts
  getAlerts: async (): Promise<Alert[]> => {
    const response = await api.get('/admin/alerts');
    return response.data;
  },

  acknowledgeAlert: async (alertId: string): Promise<void> => {
    await api.post(`/admin/alerts/${alertId}/acknowledge`);
  },

  resolveAlert: async (alertId: string): Promise<void> => {
    await api.post(`/admin/alerts/${alertId}/resolve`);
  },

  createAlert: async (alert: Omit<Alert, 'id' | 'createdAt' | 'acknowledged' | 'resolved'>): Promise<Alert> => {
    const response = await api.post('/admin/alerts', alert);
    return response.data;
  },

  deleteAlert: async (alertId: string): Promise<void> => {
    await api.delete(`/admin/alerts/${alertId}`);
  },

  // Pub/Sub Metrics
  getPubSubMetrics: async (): Promise<PubSubMetrics[]> => {
    const response = await api.get('/admin/pubsub/metrics');
    return response.data;
  },

  // System
  getSystemInfo: async (): Promise<{
    version: string;
    environment: string;
    uptime: string;
    memory: { used: number; total: number };
    cpu: number;
  }> => {
    const response = await api.get('/admin/system/info');
    return response.data;
  },

  getHealthCheck: async (): Promise<{
    status: 'healthy' | 'degraded' | 'unhealthy';
    checks: Record<string, { status: string; latency: number }>;
  }> => {
    const response = await api.get('/admin/system/health');
    return response.data;
  },
};

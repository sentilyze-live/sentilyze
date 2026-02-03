import { useEffect, useCallback, useRef } from 'react';
import { useWebSocketStore } from '../stores/websocketStore';
import { useAuthStore } from '../stores/authStore';
import { useGoldStore } from '../stores/goldStore';
import { useAdminStore } from '../stores/adminStore';

type EventHandler = (data: unknown) => void;

export function useWebSocket() {
  const { socket, isConnected, subscribe, unsubscribe, emit, connect, disconnect } = useWebSocketStore();
  const { accessToken } = useAuthStore();
  const handlersRef = useRef<Map<string, Set<EventHandler>>>(new Map());

  useEffect(() => {
    if (accessToken) {
      connect(accessToken);
    } else {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [accessToken, connect, disconnect]);

  const subscribeToChannel = useCallback((channel: string) => {
    subscribe(channel);
  }, [subscribe]);

  const unsubscribeFromChannel = useCallback((channel: string) => {
    unsubscribe(channel);
  }, [unsubscribe]);

  const addEventListener = useCallback((event: string, handler: EventHandler) => {
    if (!handlersRef.current.has(event)) {
      handlersRef.current.set(event, new Set());
    }
    handlersRef.current.get(event)!.add(handler);

    if (socket) {
      socket.on(event, handler);
    }

    return () => {
      handlersRef.current.get(event)?.delete(handler);
      if (socket) {
        socket.off(event, handler);
      }
    };
  }, [socket]);

  const removeEventListener = useCallback((event: string, handler?: EventHandler) => {
    if (socket) {
      if (handler) {
        socket.off(event, handler);
        handlersRef.current.get(event)?.delete(handler);
      } else {
        socket.off(event);
        handlersRef.current.delete(event);
      }
    }
  }, [socket]);

  const sendEvent = useCallback((event: string, data?: unknown) => {
    emit(event, data);
  }, [emit]);

  return {
    socket,
    isConnected,
    subscribe: subscribeToChannel,
    unsubscribe: unsubscribeFromChannel,
    addEventListener,
    removeEventListener,
    sendEvent,
    connect,
    disconnect,
  };
}

// Gold price updates hook
export function useGoldPrice(symbol: string = 'XAU/USD') {
  const { subscribe, unsubscribe, addEventListener, isConnected } = useWebSocket();
  const updatePrice = useGoldStore((state) => state.updatePrice);

  useEffect(() => {
    if (!isConnected) return;

    const channel = `gold:${symbol}`;
    subscribe(channel);

    const handlePriceUpdate = (data: unknown) => {
      updatePrice(data as import('../lib/api/gold').GoldPrice);
    };

    const cleanup = addEventListener('price:update', handlePriceUpdate);

    return () => {
      unsubscribe(channel);
      cleanup();
    };
  }, [symbol, isConnected, subscribe, unsubscribe, addEventListener, updatePrice]);
}

// Alerts hook
export function useAlerts() {
  const { subscribe, unsubscribe, addEventListener, isConnected } = useWebSocket();
  const fetchAlerts = useAdminStore((state) => state.fetchAlerts);
  const alertsRef = useRef<unknown[]>([]);

  useEffect(() => {
    if (!isConnected) return;

    subscribe('alerts');

    const handleNewAlert = (alert: unknown) => {
      alertsRef.current = [alert, ...alertsRef.current].slice(0, 10);
      fetchAlerts();
    };

    const cleanup = addEventListener('alert:new', handleNewAlert);

    return () => {
      unsubscribe('alerts');
      cleanup();
    };
  }, [isConnected, subscribe, unsubscribe, addEventListener, fetchAlerts]);

  return alertsRef.current;
}

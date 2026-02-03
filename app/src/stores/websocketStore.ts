import { create } from 'zustand';
import { io, Socket } from 'socket.io-client';

interface WebSocketState {
  socket: Socket | null;
  isConnected: boolean;
  connectionError: string | null;
  subscriptions: Set<string>;

  connect: (token?: string) => void;
  disconnect: () => void;
  subscribe: (channel: string) => void;
  unsubscribe: (channel: string) => void;
  emit: (event: string, data?: unknown) => void;
}

const WS_URL = import.meta.env.VITE_WS_URL || 'wss://api.sentilyze.com';

export const useWebSocketStore = create<WebSocketState>((set, get) => ({
  socket: null,
  isConnected: false,
  connectionError: null,
  subscriptions: new Set(),

  connect: (token?: string) => {
    const { socket, isConnected } = get();

    if (socket && isConnected) {
      return;
    }

    const socketInstance = io(WS_URL, {
      transports: ['websocket'],
      autoConnect: true,
      auth: token ? { token } : undefined,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });

    socketInstance.on('connect', () => {
      console.log('[WS] Connected:', socketInstance.id);
      set({ isConnected: true, connectionError: null });

      get().subscriptions.forEach((channel) => {
        socketInstance.emit('subscribe', channel);
      });
    });

    socketInstance.on('disconnect', (reason) => {
      console.log('[WS] Disconnected:', reason);
      set({ isConnected: false });
    });

    socketInstance.on('connect_error', (error) => {
      console.error('[WS] Connection error:', error);
      set({ connectionError: error.message, isConnected: false });
    });

    socketInstance.on('error', (error) => {
      console.error('[WS] Error:', error);
    });

    set({ socket: socketInstance });
  },

  disconnect: () => {
    const { socket } = get();
    if (socket) {
      socket.disconnect();
      socket.removeAllListeners();
      set({ socket: null, isConnected: false, subscriptions: new Set() });
    }
  },

  subscribe: (channel: string) => {
    const { socket, isConnected, subscriptions } = get();

    if (subscriptions.has(channel)) {
      return;
    }

    subscriptions.add(channel);

    if (socket && isConnected) {
      socket.emit('subscribe', channel);
    }
  },

  unsubscribe: (channel: string) => {
    const { socket, isConnected, subscriptions } = get();

    subscriptions.delete(channel);

    if (socket && isConnected) {
      socket.emit('unsubscribe', channel);
    }
  },

  emit: (event: string, data?: unknown) => {
    const { socket, isConnected } = get();

    if (socket && isConnected) {
      socket.emit(event, data);
    } else {
      console.warn('[WS] Cannot emit, not connected');
    }
  },
}));

export const useWebSocket = () => {
  const { socket, isConnected, subscribe, unsubscribe, emit } = useWebSocketStore();

  return { socket, isConnected, subscribe, unsubscribe, emit };
};

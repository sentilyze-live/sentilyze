import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi, type User, type LoginRequest, type RegisterRequest } from '../lib/api/auth';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (credentials) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.login(credentials);
          set({ user: response.user, accessToken: response.accessToken, refreshToken: response.refreshToken, isAuthenticated: true, isLoading: false });
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Giriş başarısız', isLoading: false });
          throw error;
        }
      },

      register: async (data) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.register(data);
          set({ user: response.user, accessToken: response.accessToken, refreshToken: response.refreshToken, isAuthenticated: true, isLoading: false });
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Kayıt başarısız', isLoading: false });
          throw error;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        try { await authApi.logout(); } catch (error) { console.error('Logout error:', error); }
        finally { set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false, isLoading: false, error: null }); }
      },

      refresh: async () => {
        const { refreshToken } = get();
        if (!refreshToken) { get().logout(); return; }
        try {
          const response = await authApi.refresh();
          set({ accessToken: response.accessToken, refreshToken: response.refreshToken });
        } catch (error) { get().logout(); throw error; }
      },

      checkAuth: async () => {
        const { accessToken, refreshToken } = get();
        if (!accessToken && !refreshToken) { set({ isAuthenticated: false }); return; }
        set({ isLoading: true });
        try {
          const user = await authApi.me();
          set({ user, isAuthenticated: true, isLoading: false });
        } catch (error) { set({ user: null, isAuthenticated: false, isLoading: false }); }
      },

      clearError: () => set({ error: null }),
    }),
    { name: 'auth-storage', partialize: (state) => ({ accessToken: state.accessToken, refreshToken: state.refreshToken, user: state.user, isAuthenticated: state.isAuthenticated }) }
  )
);

export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);
export const useAuthError = () => useAuthStore((state) => state.error);

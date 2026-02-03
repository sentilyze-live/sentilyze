import { useCallback } from 'react';
import { useAuthStore } from '../stores/authStore';
import type { LoginRequest, RegisterRequest } from '../lib/api/auth';

export function useAuth() {
  const { login, register, logout, refresh, checkAuth, isLoading, error, isAuthenticated, user, clearError } = useAuthStore();

  const handleLogin = useCallback(async (credentials: LoginRequest) => login(credentials), [login]);
  const handleRegister = useCallback(async (data: RegisterRequest) => register(data), [register]);
  const handleLogout = useCallback(async () => logout(), [logout]);
  const handleRefresh = useCallback(async () => refresh(), [refresh]);
  const handleCheckAuth = useCallback(async () => checkAuth(), [checkAuth]);

  return { user, isAuthenticated, isLoading, error, login: handleLogin, register: handleRegister, logout: handleLogout, refresh: handleRefresh, checkAuth: handleCheckAuth, clearError };
}

export function useProtectedRoute() {
  const { isAuthenticated, isLoading, checkAuth } = useAuth();
  return { isAuthenticated, isLoading, checkAuth };
}

export function useAuthState() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isLoading = useAuthStore((state) => state.isLoading);
  const user = useAuthStore((state) => state.user);
  const error = useAuthStore((state) => state.error);
  return { isAuthenticated, isLoading, user, error };
}

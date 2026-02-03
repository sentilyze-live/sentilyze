import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { toast } from 'sonner';

// Turkish error messages
const TURKISH_ERRORS: Record<string, string> = {
  'auth/invalid-email': 'Geçersiz e-posta adresi',
  'auth/user-disabled': 'Bu hesap devre dışı bırakıldı',
  'auth/user-not-found': 'Kullanıcı bulunamadı',
  'auth/wrong-password': 'Yanlış şifre',
  'auth/email-already-in-use': 'Bu e-posta zaten kayıtlı',
  'auth/weak-password': 'Şifre çok zayıf',
  'auth/operation-not-allowed': 'Bu işlem izin verilmiyor',
  'auth/network-request-failed': 'Ağ hatası, lütfen internet bağlantınızı kontrol edin',
  '401': 'Oturumunuz süresi doldu, lütfen tekrar giriş yapın',
  '403': 'Bu işlem için yetkiniz yok',
  '404': 'İstenen kaynak bulunamadı',
  '429': 'Çok fazla istek, lütfen bekleyin',
  '500': 'Sunucu hatası, lütfen daha sonra tekrar deneyin',
  '502': 'Sunucu şu anda kullanılamıyor',
  '503': 'Hizmet geçici olarak kullanılamıyor',
};

export const getTurkishErrorMessage = (error: AxiosError): string => {
  const status = error.response?.status?.toString();
  const message = error.response?.data?.message;
  
  if (status && TURKISH_ERRORS[status]) {
    return TURKISH_ERRORS[status];
  }
  
  if (message && typeof message === 'string' && TURKISH_ERRORS[message]) {
    return TURKISH_ERRORS[message];
  }
  
  if (error.message) {
    if (error.message.includes('Network Error')) {
      return 'Ağ bağlantısı yok, lütfen internet bağlantınızı kontrol edin';
    }
  }
  
  return 'Beklenmeyen bir hata oluştu';
};

// Generate unique request ID
const generateRequestId = (): string => {
  return `req_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
};

// Create axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'https://api.sentilyze.com/api/v1',
  withCredentials: true,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add request ID
    config.headers['X-Request-ID'] = generateRequestId();
    
    // Add timestamp
    config.headers['X-Client-Time'] = new Date().toISOString();
    
    // Log request in development
    if (import.meta.env.DEV) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, {
        requestId: config.headers['X-Request-ID'],
        timestamp: config.headers['X-Client-Time'],
      });
    }
    
    return config;
  },
  (error: AxiosError) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    // Log response in development
    if (import.meta.env.DEV) {
      console.log(
        `[API] Response ${response.status}`,
        response.config.url,
        response.data
      );
    }
    
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config;
    
    // Handle 401 - Token refresh
    if (error.response?.status === 401 && originalRequest) {
      try {
        // Attempt to refresh token
        await api.post('/auth/refresh');
        // Retry original request
        return api(originalRequest);
      } catch (refreshError) {
        // Redirect to login
        if (typeof window !== 'undefined') {
          window.location.href = '/auth/login';
        }
        return Promise.reject(refreshError);
      }
    }
    
    // Handle 403 - Logout
    if (error.response?.status === 403) {
      toast.error(TURKISH_ERRORS['403']);
      // Could trigger logout here if needed
    }
    
    // Handle 429 - Rate limiting
    if (error.response?.status === 429) {
      const retryAfter = error.response.headers['retry-after'];
      const message = retryAfter
        ? `Çok fazla istek. ${retryAfter} saniye sonra tekrar deneyin.`
        : TURKISH_ERRORS['429'];
      toast.warning(message);
    }
    
    // Handle 500+ server errors
    if (error.response?.status && error.response.status >= 500) {
      const errorMessage = getTurkishErrorMessage(error);
      toast.error(errorMessage);
    }
    
    // Log error in development
    if (import.meta.env.DEV) {
      console.error('[API] Response error:', {
        status: error.response?.status,
        message: error.response?.data,
        url: originalRequest?.url,
      });
    }
    
    return Promise.reject(error);
  }
);

export default api;

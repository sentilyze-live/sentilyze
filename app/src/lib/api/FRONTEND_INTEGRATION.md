# SENTILYZE Frontend Integration Guide

## Overview
This document describes the frontend-backend integration for the SENTILYZE platform.

## Backend Endpoints
- **API Gateway**: `https://api.sentilyze.com/api/v1`
- **WebSocket**: `wss://api.sentilyze.com`
- **Admin Panel**: `https://admin.sentilyze.com`

## Directory Structure

```
app/src/
├── lib/
│   └── api/
│       ├── client.ts      # Axios client with interceptors
│       ├── auth.ts        # Authentication endpoints
│       ├── gold.ts        # Gold price/data endpoints
│       ├── public.ts      # Public endpoints
│       └── admin.ts       # Admin panel endpoints
├── stores/
│   ├── authStore.ts       # Auth state management
│   ├── goldStore.ts       # Gold data state
│   ├── adminStore.ts      # Admin panel state
│   └── websocketStore.ts  # WebSocket state
├── hooks/
│   ├── useAuth.ts         # Auth hooks
│   ├── useGoldData.ts     # Gold data hooks
│   ├── useAdminData.ts    # Admin data hooks
│   └── useWebSocket.ts    # WebSocket hooks
└── components/
    └── gold/
        ├── GoldChart.tsx      # Chart component
        ├── GoldHeader.tsx      # Price header
        └── ...
```

## API Client Features

### Request Interceptor
- Adds `Authorization` header with JWT token
- Adds `X-Request-ID` for tracing
- Adds `X-Client-Time` timestamp

### Response Interceptor
- Handles 401: Token refresh
- Handles 403: Logout
- Handles 429: Rate limiting with retry
- Handles 500+: Error toasts with Turkish messages

## Usage Examples

### Authentication
```typescript
import { useAuth } from './hooks';

const LoginForm = () => {
  const { login, isLoading, error } = useAuth();
  
  const handleSubmit = async (email: string, password: string) => {
    await login({ email, password });
  };
};
```

### Gold Data
```typescript
import { useGoldData } from './hooks';

const GoldDashboard = () => {
  const { price, history, predictions, isLoading } = useGoldData('XAU/USD');
  
  if (isLoading.price) return <LoadingSkeleton />;
  
  return (
    <div>
      <PriceDisplay value={price.price} change={price.change} />
      <Chart data={history} />
      <PredictionsList predictions={predictions} />
    </div>
  );
};
```

### Real-time Updates
```typescript
import { useGoldPrice } from './hooks';

const LivePrice = () => {
  const { price } = useGoldStore();
  useGoldPrice('XAU/USD');
  
  return <span>{price?.price}</span>;
};
```

## Environment Variables

```env
VITE_API_URL=https://api.sentilyze.com/api/v1
VITE_WS_URL=wss://api.sentilyze.com
VITE_ENV=production
```

## Turkish Locale Formatting

All numbers use Turkish format:
- Decimals: `43.080,50`
- Dates: `3 Şub 2026, 15:30`
- Currency: `₺430.800,50`

## Error Handling

Errors are displayed in Turkish:
- 401: "Oturumunuz süresi doldu"
- 403: "Bu işlem için yetkiniz yok"
- 429: "Çok fazla istek"
- 500: "Sunucu hatası"

## WebSocket Events

### Subscribe
```typescript
socket.emit('subscribe', 'gold:XAU/USD');
socket.emit('subscribe', 'alerts');
```

### Listen
- `price:update` - Real-time price updates
- `alert:new` - New alert notifications

# Sentilyze iOS App - Gelistirme Notlari

> Bu dosya ayri bir session'da iOS uygulamayi gelistirmek icin hazirlanmistir.

---

## 1. MIMARI KARAR: React Native + Expo

### Neden Expo SDK 52+?
- Mevcut React 19 / TypeScript / Zustand frontend ile **%60-70 kod paylasimi**
- `goldStore.ts`, `gold.ts` tipleri, `format.ts` utility'leri dogrudan tasinabilir
- Expo Router = dosya tabanli navigasyon (web'deki react-router-dom'a benzer)
- Expo Notifications + FCM ile push bildirimler
- EAS Build ile CI/CD
- Apple TestFlight dagitimi dahili

### Tech Stack
```
expo@52+
  ├── expo-router (file-based navigation)
  ├── nativewind@4 (Tailwind for RN)
  ├── zustand@5 (ayni store yapisi)
  ├── @tanstack/react-query@5 (API caching)
  ├── axios@1.x (ayni API client)
  ├── react-native-wagmi-charts (finansal grafikler)
  ├── socket.io-client@4 (canli fiyatlar)
  ├── expo-notifications (push)
  ├── react-native-reanimated (animasyonlar)
  ├── expo-haptics (titresim geri bildirimi)
  └── revenue-cat (abonelik yonetimi - App Store)
```

---

## 2. PAYLASILAN KOD - DOGRUDAN TASINACAKLAR

### 2.1 Store Yapisi (goldStore.ts)
Zustand React Native'de ayni sekilde calisir. Degisiklik gerekmez:
- 12 data slice (price, history, predictions, indicators, sentiment, spikes, correlations, scenarios, dailyReport, context, correlationDetails)
- Granular loading/error state'leri
- 30 saniye stale data threshold
- `fetchAll()` paralel veri cekme

### 2.2 API Tipleri (gold.ts) - %100 Portatif
13 interface dogrudan kopyalanir:
- GoldPrice, GoldHistory, Prediction, TechnicalIndicators
- SentimentData, SpikeData, CorrelationData, NewsArticle
- ScenarioData, DailyReportData, MarketContextData, CorrelationDetail

### 2.3 API Client (client.ts)
Axios React Native'de calisir. Kucuk degisiklikler:
- `import.meta.env.VITE_API_URL` -> `process.env.EXPO_PUBLIC_API_URL`
- Request/response interceptor'lar ayni kalir
- Turkce hata mesajlari ayni kalir

### 2.4 Format Utilities (format.ts)
6 fonksiyon dogrudan tasinir:
- `formatTurkishNumber()` - Intl.NumberFormat RN'de calisir
- `formatTurkishPrice()` - Ayni
- `formatCurrency()` - Ayni
- `formatPercentage()` - Ayni
- `formatDate()` - Ayni
- `formatTimeAgo()` - Ayni

---

## 3. FIYATLANDIRMA MODELI

### Ucretsiz Tier
- Canli altin fiyatlari (XAU/USD, gram, ceyrek, yarim, tam)
- Temel grafikler (1G, 1H, 1A)
- Gunluk piyasa ozeti (1/gun)
- 3 teknik gosterge (RSI, MACD, Bollinger)
- 2 fiyat alarmi
- Reklam destekli

### Profesyonel - 79.99 TL/ay (~$2.30)
- Tum ucretsiz ozellikler +
- AI tahminleri (15dk - 6sa)
- Tam teknik analiz (Ichimoku, Fibonacci, Pivot, Keltner)
- Sentiment analizi
- Korelasyon matrisi (DXY, Treasury, VIX, S&P 500, BTC)
- Ensemble model tahminleri + guven skorlari
- Rejim tespiti
- Sinirsiz push bildirim
- Haftalik AI Analyst raporu
- Reklamsiz

### Elmas - 199.99 TL/ay (~$5.75)
- Tum profesyonel ozellikler +
- Kisisel AI chatbot (Claude Opus)
- Ozel watchlist'ler
- Fusion sinyal alarmlari
- Divergence algilamalari
- Oncelikli veri yenileme (15sn vs 60sn)
- Excel/PDF export
- TCMB karar analizi

### RevenueCat Entegrasyonu
```typescript
// RevenueCat setup - App.tsx
import Purchases from 'react-native-purchases';

Purchases.configure({
  apiKey: 'appl_XXXXXX', // Apple API key
});

// Offerings
const offerings = await Purchases.getOfferings();
// "pro_monthly" -> 79.99 TL
// "diamond_monthly" -> 199.99 TL
// "pro_yearly" -> 699.99 TL (%27 indirim)
// "diamond_yearly" -> 1799.99 TL (%25 indirim)
```

---

## 4. EKRAN YAPISI

```
app/
├── (tabs)/
│   ├── index.tsx          # Ana ekran - Canli fiyat + mini grafik
│   ├── analysis.tsx       # Teknik analiz + tahminler
│   ├── signals.tsx        # Fusion sinyalleri + alarmlar
│   ├── news.tsx           # Haberler + sentiment
│   └── profile.tsx        # Profil + abonelik + ayarlar
├── chart/
│   └── [timeframe].tsx    # Tam ekran grafik
├── prediction/
│   └── [id].tsx           # Tahmin detayi
├── settings/
│   ├── notifications.tsx  # Bildirim ayarlari
│   └── subscription.tsx   # Abonelik yonetimi
├── calculator/
│   └── index.tsx          # Gram altin hesaplayici
└── _layout.tsx            # Root layout
```

---

## 5. TURKIYE'YE OZEL OZELLIKLER

### 5.1 Gram Altin Hesaplayici (VIRAL POTANSIYEL)
- Gram, ceyrek, yarim, tam, cumhuriyet altini donusum
- "X TL ile kac gram alirim?" hesaplayicisi
- Turkiye'de en cok aranan altin ozelligi
- Widget olarak da sunulabilir

### 5.2 Kapali Carsi Canli
- Spot fiyattan %2-5 farkli
- Turk kullanicilari icin olmazsa olmaz

### 5.3 Cumhuriyet Altini Premium/Iskonto
- Priminin spot altina oranini takip
- Kendi basina bir ticaret sinyali

### 5.4 Dugun Butcesi Hesaplayici
- AI tahminleri ile 3-12 ay sonraki maliyet projeksiyonu
- Viral potansiyel

### 5.5 TCMB Faiz Karari Analizi
- Otomatik etki analizi

---

## 6. MOBIL-NATIVE OZELLIKLER

### 6.1 Apple Watch Complication
```swift
// WatchKit Extension
// Gram altin fiyatini saat yuzunde goster
// ClockKit ComplicationProvider
// Tek basina abonelik nedeni
```

### 6.2 Lock Screen Widget (iOS 16+)
```swift
// ActivityKit + Live Activities
// Canli altin fiyat hareketi
// WidgetKit Timeline Provider
```

### 6.3 Siri Shortcuts
```swift
// "Hey Siri, altin ne kadar?"
// INIntent -> API call -> spoken response
```

### 6.4 Haptic Fiyat Alarmlari
```typescript
import * as Haptics from 'expo-haptics';

// Spike: Heavy impact
Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);

// Tahmin degisimi: Light
Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

// Divergence: Notification warning
Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
```

### 6.5 Cevrimdisi Mod
- Son 24 saatin verileri + teknik gostergeler AsyncStorage'da
- Metro/ucak kullanimi

### 6.6 Paylasim Kartlari
- Tek dokunusla Sentilyze filigranli grafik screenshot
- Instagram/Twitter paylasimi -> viral buyume

---

## 7. API ENDPOINT'LERI

Mevcut backend endpoint'leri iOS icin hazir:

```
BASE_URL: https://api-gateway-koa62feuuq-uc.a.run.app

GET  /gold/price?symbol=XAU/USD
GET  /gold/history?symbol=XAU/USD&timeframe=1h&limit=100
GET  /gold/predictions?symbol=XAU/USD&timeframe=1h
GET  /gold/technical-indicators?symbol=XAU/USD
GET  /gold/sentiment?symbol=XAU/USD
GET  /gold/spikes?symbol=XAU/USD&threshold=1.0
GET  /gold/correlations?symbol=XAU/USD
GET  /gold/news?symbol=XAU/USD&page=1&limit=20
GET  /gold/scenarios?symbol=XAU/USD
GET  /gold/daily-report
GET  /gold/context?symbol=XAU/USD
GET  /gold/correlation?symbol=XAU/USD&compare_with=DXY,BTC
WS   /ws (real-time updates)
```

---

## 8. GELIR PROJEKSIYONU

| Metrik | 3. Ay | 6. Ay | 12. Ay |
|--------|-------|-------|--------|
| Ucretsiz indirme | 5,000 | 15,000 | 50,000 |
| Pro abone (%3-4) | 150 | 600 | 2,000 |
| Elmas abone (%0.5) | 25 | 75 | 250 |
| Aylik Pro gelir | 12,000 TL | 48,000 TL | 160,000 TL |
| Aylik Elmas gelir | 5,000 TL | 15,000 TL | 50,000 TL |
| **Net (Apple kesintisi sonrasi)** | **~$345** | **~$1,270** | **~$4,220** |

---

## 9. GELISTIRME ADIMLARI (SESSION PLANI)

### Session 1: Proje Kurulumu
1. `npx create-expo-app sentilyze-mobile --template tabs`
2. NativeWind + Tailwind kurulumu
3. Zustand store tasima (goldStore.ts)
4. API client + tipler tasima
5. Temel navigasyon

### Session 2: Ana Ekranlar
1. Canli fiyat ekrani + mini grafik
2. Teknik analiz ekrani
3. Tahmin ekrani
4. Haber/sentiment ekrani

### Session 3: Grafik + Veri Gorsellestirme
1. react-native-wagmi-charts entegrasyonu
2. Interaktif grafik (pinch-zoom, crosshair)
3. Korelasyon matrisi gorsel

### Session 4: Premium Ozellikler
1. RevenueCat abonelik akisi
2. Push notification (Expo Notifications)
3. Gram altin hesaplayici
4. Paywall / tier-based gating

### Session 5: Native Ozellikler
1. Apple Watch widget
2. Lock Screen widget
3. Haptic feedback
4. Cevrimdisi mod

### Session 6: Polish + Yayinlama
1. App Store assets (screenshots, description)
2. TestFlight beta
3. App Store Connect submission
4. ASO (App Store Optimization)

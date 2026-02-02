# Frontend UI Tasarlama Rehberi
## Sentilyze Web Platformu

---

## 📋 İçindekiler

1. [Genel Bakış](#genel-bakış)
2. [Tasarım Felsefesi](#tasarım-felsefesi)
3. [Teknoloji Stack](#teknoloji-stack)
4. [Sayfa Yapıları](#sayfa-yapıları)
5. [Komponent Kütüphanesi](#komponent-kütüphanesi)
6. [Renk Paleti ve Tipografi](#renk-paleti-ve-tipografi)
7. [Responsive Tasarım](#responsive-tasarım)
8. [Animasyonlar ve İnteraksiyonlar](#animasyonlar-ve-interaksiyonlar)
9. [Veri Görselleştirme](#veri-görselleştirme)
10. [Adım Adım Uygulama](#adım-adım-uygulama)

---

## 🎯 Genel Bakış

Sentilyze frontend'i, **modern, temiz ve kullanıcı dostu** bir arayüz sunmak üzere tasarlanmıştır. Kullanıcılar, karmaşık finansal verileri kolayca anlayabilmeli ve platform üzerinde rahatça gezinebilmelidir.

### Hedef Kullanıcılar

1. **Bireysel Yatırımcılar**: Kripto ve altın piyasasını takip eden kişiler
2. **Profesyonel Traderlar**: Teknik analiz ve sentiment verileri arayan uzmanlar
3. **Analistler**: Piyasa araştırması yapan finansal analistler
4. **Meraklılar**: Piyasa trendlerini öğrenmek isteyen kişiler

### Platform Hedefleri

- ✅ Basit ve anlaşılır arayüz
- ✅ Hızlı veri erişimi
- ✅ Görsel olarak çekici grafikler
- ✅ Mobil uyumlu tasarım
- ✅ Erişilebilir (accessibility)

---

## 🎨 Tasarım Felsefesi

### Temel Prensipler

#### 1. **Clarity (Netlik)**
Her element açıkça ne işe yaradığını göstermeli. Kullanıcı kafasını karıştıracak belirsizlik olmamalı.

#### 2. **Simplicity (Basitlik)**
Minimal tasarım. Gereksiz elementlerden kaçınılmalı. Her sayfa tek bir amaca odaklanmalı.

#### 3. **Consistency (Tutarlılık)**
Tüm sayfalarda aynı tasarım dili kullanılmalı. Renkler, fontlar, spacing tutarlı olmalı.

#### 4. **Hierarchy (Hiyerarşi)**
Bilgi önceliğine göre düzenlenmeli. En önemli bilgiler en üstte ve büyük olmalı.

#### 5. **Feedback (Geri Bildirim)**
Kullanıcı her aksiyonu aldığında feedback almalı (loading states, success messages, errors).

---

## 💻 Teknoloji Stack

### Core Framework

```
Next.js 14 (App Router)
├── React 18
├── TypeScript
└── Node.js 18+
```

### Styling

```
Tailwind CSS
├── Utility-first approach
├── Custom theme
└── Dark mode support
```

### UI Components

```
shadcn/ui
├── Radix UI primitives
├── Accessible components
└── Customizable
```

### Data Visualization

```
Recharts / Chart.js
├── Interactive charts
├── Responsive
└── Customizable
```

### State Management

```
React Context
├── Feature flags
├── User preferences
└── Theme
```

### API Integration

```
Next.js API Routes
├── Backend proxy
├── Server-side rendering
└── API caching
```

---

## 🏗️ Sayfa Yapıları

### 1. Landing Page (Ana Sayfa)

**URL**: `/`

**Amaç**: Platformu tanıtmak, kullanıcıları kayıt olmaya teşvik etmek

**Bölümler**:

```
┌─────────────────────────────────────────────┐
│           NAVBAR (Sticky)                    │
├─────────────────────────────────────────────┤
│                                              │
│           HERO SECTION                       │
│  - Başlık: "Piyasa Duygusunu Oku"          │
│  - Alt Başlık: Açıklama                     │
│  - CTA Buttons: [Ücretsiz Dene] [Demo Gör] │
│  - Hero Image/Animation                     │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           FEATURES SECTION                   │
│  Grid (3 sütun)                             │
│  - AI-Powered Analysis                      │
│  - Real-time Data                           │
│  - Smart Alerts                             │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           HOW IT WORKS                       │
│  Timeline/Stepper (4 adım)                  │
│  1. Veri Toplama                            │
│  2. AI Analizi                              │
│  3. İçgörü Üretimi                          │
│  4. Bildirim                                │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           LIVE DEMO SECTION                  │
│  - Örnek sentiment chart                    │
│  - Gerçek zamanlı data feed                 │
│  - "Daha fazla gör" CTA                     │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           PRICING SECTION                    │
│  Cards (3 plan)                             │
│  - Ücretsiz                                 │
│  - Profesyonel                              │
│  - Kurumsal                                 │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           TESTIMONIALS                       │
│  Slider (kullanıcı yorumları)               │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           CTA SECTION                        │
│  - "Bugün başlayın" başlığı                 │
│  - Email signup form                        │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           FOOTER                             │
│  - Links (About, Blog, Contact)             │
│  - Social media                             │
│  - Legal (Yasal Uyarı)                      │
│                                              │
└─────────────────────────────────────────────┘
```

**Tasarım Notları**:
- Hero section full-screen, gradient background
- Sticky header şeffaf, scroll sonrası solid
- Smooth scroll animations (AOS, Framer Motion)
- Dark mode toggle

---

### 2. Gold Dashboard (Altın Panosu)

**URL**: `/altin`

**Amaç**: Altın piyasası hakkında gerçek zamanlı veriler ve sentiment analizi

**Layout**:

```
┌─────────────────────────────────────────────────────────────┐
│  NAVBAR (Dashboard variant)                                  │
├────────────────────┬────────────────────────────────────────┤
│                    │                                         │
│  SIDEBAR           │         MAIN CONTENT                    │
│  (Desktop only)    │                                         │
│                    │  ┌───────────────────────────────────┐ │
│  - Dashboard       │  │   HEADER                          │ │
│  - Altın           │  │   Altın Piyasası • Son Güncelleme │ │
│  - Kripto          │  └───────────────────────────────────┘ │
│  - Ayarlar         │                                         │
│  - Çıkış           │  ┌───────────────────────────────────┐ │
│                    │  │   KPI CARDS (Grid 4 col)          │ │
│                    │  │   ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐│ │
│                    │  │   │Price│ │24h %│ │Sent.│ │Vol. ││ │
│                    │  │   └─────┘ └─────┘ └─────┘ └─────┘│ │
│                    │  └───────────────────────────────────┘ │
│                    │                                         │
│                    │  ┌───────────────────────────────────┐ │
│                    │  │   PRICE CHART (Large)              │ │
│                    │  │   Candlestick / Line Chart         │ │
│                    │  │   Timeframe: 1D 1W 1M 3M 1Y       │ │
│                    │  └───────────────────────────────────┘ │
│                    │                                         │
│                    │  ┌──────────────────┬────────────────┐ │
│                    │  │ SENTIMENT GAUGE  │ NEWS FEED      │ │
│                    │  │ Circular progress│ Latest news    │ │
│                    │  │ 0-100 score      │ with sentiment │ │
│                    │  └──────────────────┴────────────────┘ │
│                    │                                         │
│                    │  ┌───────────────────────────────────┐ │
│                    │  │   TECHNICAL INDICATORS             │ │
│                    │  │   RSI, MACD, Bollinger Bands      │ │
│                    │  └───────────────────────────────────┘ │
│                    │                                         │
└────────────────────┴─────────────────────────────────────────┘
```

**Tasarım Notları**:
- Real-time data updates (polling veya WebSocket)
- Interactive charts (Recharts / Chart.js)
- Color-coded sentiment (Red: Negative, Green: Positive)
- Loading skeletons during data fetch
- Error boundaries

---

### 3. Analysis Page (Detaylı Analiz)

**URL**: `/altin/analysis`

**Amaç**: Derin analiz ve teknik göstergeler

**Layout**:

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER                                                      │
│  Altın Detaylı Analiz                                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  TABS                                                        │
│  [Genel] [Teknik] [Sentiment] [Haberler] [Sosyal]         │
└─────────────────────────────────────────────────────────────┘

TAB: GENEL
┌──────────────────────────────────────────────────────────────┐
│  ┌────────────────────┬──────────────────────────────────┐  │
│  │  OVERVIEW          │  MARKET STATS                    │  │
│  │  - Current Price   │  - Volume                        │  │
│  │  - 24h Change      │  - Market Cap                    │  │
│  │  - Sentiment Score │  - 52w High/Low                  │  │
│  └────────────────────┴──────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  PRICE HISTORY CHART (Multi-timeframe)               │  │
│  │  [1D] [1W] [1M] [3M] [6M] [1Y] [ALL]                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  CORRELATIONS                                        │   │
│  │  - USD Strength: -0.75                              │   │
│  │  - Bitcoin: 0.45                                    │   │
│  │  - Oil: 0.30                                        │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘

TAB: TEKNİK
┌──────────────────────────────────────────────────────────────┐
│  ┌──────────────────────────────────────────────────────┐  │
│  │  TECHNICAL INDICATORS (Grid 2x2)                     │  │
│  │  ┌─────────────────┬─────────────────┐              │  │
│  │  │ RSI Chart       │ MACD Chart      │              │  │
│  │  └─────────────────┴─────────────────┘              │  │
│  │  ┌─────────────────┬─────────────────┐              │  │
│  │  │ Bollinger Bands │ Moving Averages │              │  │
│  │  └─────────────────┴─────────────────┘              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  SUPPORT & RESISTANCE                                 │  │
│  │  Chart with horizontal lines                          │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘

TAB: SENTIMENT
┌──────────────────────────────────────────────────────────────┐
│  ┌────────────────────┬──────────────────────────────────┐  │
│  │  SENTIMENT GAUGE   │  SENTIMENT TREND                 │  │
│  │  Current: 65/100   │  Line chart (last 7 days)       │  │
│  └────────────────────┴──────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  SENTIMENT BY SOURCE                                  │  │
│  │  Bar chart                                            │  │
│  │  Twitter: 70, Reddit: 60, News: 55                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  KEYWORD CLOUD                                        │  │
│  │  bullish, inflation, hedge, safe-haven...            │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**Tasarım Notları**:
- Tabs için shadcn/ui Tabs component
- Charts için Recharts (responsive)
- Data refresh button (manuel yenileme)
- Export data button (CSV, PDF)

---

### 4. Admin Panel

**URL**: `/admin`

**Amaç**: Platform yönetimi (feature flags, kullanıcılar, costs)

**Layout**:

```
┌─────────────────────────────────────────────────────────────┐
│  ADMIN HEADER                                                │
│  [Logo] Admin Panel         [Notifications] [User Menu]     │
└─────────────────────────────────────────────────────────────┘

┌────────────────────┬────────────────────────────────────────┐
│  ADMIN SIDEBAR     │         ADMIN CONTENT                   │
│                    │                                         │
│  - Dashboard       │  ┌───────────────────────────────────┐ │
│  - Users           │  │   STATS CARDS                     │ │
│  - Feature Flags   │  │   [Total Users] [Active] [Cost]   │ │
│  - Costs           │  └───────────────────────────────────┘ │
│  - Logs            │                                         │
│  - Settings        │  ┌───────────────────────────────────┐ │
│                    │  │   FEATURE FLAGS TABLE             │ │
│                    │  │   Name | Status | Last Modified   │ │
│                    │  │   ─────────────────────────────   │ │
│                    │  │   ENABLE_GOLD_DATA | ✓ | 2h ago  │ │
│                    │  │   [Edit] [Delete]                 │ │
│                    │  └───────────────────────────────────┘ │
│                    │                                         │
│                    │  ┌───────────────────────────────────┐ │
│                    │  │   COST BREAKDOWN (Pie Chart)      │ │
│                    │  │   Cloud Run: 40%                  │ │
│                    │  │   BigQuery: 30%                   │ │
│                    │  │   Others: 30%                     │ │
│                    │  └───────────────────────────────────┘ │
│                    │                                         │
└────────────────────┴─────────────────────────────────────────┘
```

**Tasarım Notları**:
- Authentication required (JWT)
- Role-based access control
- Audit logs
- Real-time updates (cost tracking)

---

## 🎨 Komponent Kütüphanesi

### Core Components (shadcn/ui)

#### 1. Button

```tsx
import { Button } from "@/components/ui/button"

// Variants
<Button variant="default">Primary</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="outline">Outline</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="destructive">Delete</Button>

// Sizes
<Button size="sm">Small</Button>
<Button size="default">Default</Button>
<Button size="lg">Large</Button>
```

#### 2. Card

```tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"

<Card>
  <CardHeader>
    <CardTitle>Altın Fiyatı</CardTitle>
  </CardHeader>
  <CardContent>
    <p className="text-3xl font-bold">$2,045.50</p>
    <p className="text-green-600">+2.3%</p>
  </CardContent>
</Card>
```

#### 3. Tabs

```tsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"

<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview">Genel</TabsTrigger>
    <TabsTrigger value="technical">Teknik</TabsTrigger>
    <TabsTrigger value="sentiment">Sentiment</TabsTrigger>
  </TabsList>
  <TabsContent value="overview">
    <OverviewTab />
  </TabsContent>
  {/* ... */}
</Tabs>
```

### Custom Components

#### 1. SentimentGauge

**Kullanım**: Sentiment skorunu görsel olarak gösterme

```tsx
// components/sentiment-gauge.tsx
interface SentimentGaugeProps {
  score: number; // 0-100
  size?: 'sm' | 'md' | 'lg';
}

export function SentimentGauge({ score, size = 'md' }: SentimentGaugeProps) {
  const color = score > 60 ? 'green' : score > 40 ? 'yellow' : 'red';
  
  return (
    <div className="relative w-32 h-32">
      <svg className="transform -rotate-90">
        <circle
          cx="64"
          cy="64"
          r="56"
          stroke="currentColor"
          strokeWidth="8"
          fill="none"
          className="text-gray-200"
        />
        <circle
          cx="64"
          cy="64"
          r="56"
          stroke={color}
          strokeWidth="8"
          fill="none"
          strokeDasharray={`${(score / 100) * 352} 352`}
          className="transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-2xl font-bold">{score}</span>
      </div>
    </div>
  );
}
```

**Kullanım**:
```tsx
<SentimentGauge score={75} size="lg" />
```

#### 2. PriceCard

**Kullanım**: Fiyat ve değişim bilgisi kartı

```tsx
// components/price-card.tsx
interface PriceCardProps {
  asset: string;
  price: number;
  change24h: number;
  currency?: string;
}

export function PriceCard({ asset, price, change24h, currency = 'USD' }: PriceCardProps) {
  const isPositive = change24h >= 0;
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-gray-600">
          {asset}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline space-x-2">
          <span className="text-3xl font-bold">
            ${price.toLocaleString()}
          </span>
          <span className="text-sm text-gray-500">{currency}</span>
        </div>
        <div className={`flex items-center mt-2 ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
          {isPositive ? '↑' : '↓'}
          <span className="ml-1 font-semibold">
            {Math.abs(change24h).toFixed(2)}%
          </span>
          <span className="ml-1 text-xs text-gray-500">24h</span>
        </div>
      </CardContent>
    </Card>
  );
}
```

#### 3. NewsItem

**Kullanım**: Haber feed item

```tsx
// components/news-item.tsx
interface NewsItemProps {
  title: string;
  source: string;
  timestamp: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  url: string;
}

export function NewsItem({ title, source, timestamp, sentiment, url }: NewsItemProps) {
  const sentimentColor = {
    positive: 'text-green-600',
    negative: 'text-red-600',
    neutral: 'text-gray-600'
  }[sentiment];

  return (
    <a href={url} target="_blank" rel="noopener noreferrer" 
       className="block p-4 hover:bg-gray-50 transition-colors border-b">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h4 className="font-medium text-gray-900 line-clamp-2">
            {title}
          </h4>
          <div className="flex items-center mt-2 text-sm text-gray-500">
            <span>{source}</span>
            <span className="mx-2">•</span>
            <span>{timestamp}</span>
          </div>
        </div>
        <div className={`ml-4 px-2 py-1 rounded text-xs font-medium ${sentimentColor}`}>
          {sentiment}
        </div>
      </div>
    </a>
  );
}
```

---

## 🎨 Renk Paleti ve Tipografi

### Renk Sistemi

#### Primary Colors

```css
/* tailwind.config.ts */
colors: {
  primary: {
    50: '#f0f9ff',
    100: '#e0f2fe',
    200: '#bae6fd',
    300: '#7dd3fc',
    400: '#38bdf8',
    500: '#0ea5e9', /* Main brand color */
    600: '#0284c7',
    700: '#0369a1',
    800: '#075985',
    900: '#0c4a6e',
  }
}
```

#### Sentiment Colors

```css
colors: {
  sentiment: {
    positive: '#10b981', /* Green */
    negative: '#ef4444', /* Red */
    neutral: '#6b7280',  /* Gray */
  }
}
```

#### Background Colors

```css
colors: {
  background: {
    light: '#ffffff',
    dark: '#0f172a',
  },
  surface: {
    light: '#f8fafc',
    dark: '#1e293b',
  }
}
```

### Tipografi

```css
/* tailwind.config.ts */
fontFamily: {
  sans: ['Inter', 'system-ui', 'sans-serif'],
  mono: ['Fira Code', 'monospace'],
}

fontSize: {
  'xs': '0.75rem',     /* 12px */
  'sm': '0.875rem',    /* 14px */
  'base': '1rem',      /* 16px */
  'lg': '1.125rem',    /* 18px */
  'xl': '1.25rem',     /* 20px */
  '2xl': '1.5rem',     /* 24px */
  '3xl': '1.875rem',   /* 30px */
  '4xl': '2.25rem',    /* 36px */
  '5xl': '3rem',       /* 48px */
}
```

**Kullanım**:
```tsx
<h1 className="text-4xl font-bold text-gray-900">
  Başlık
</h1>
<p className="text-base text-gray-600">
  Paragraph text
</p>
```

---

## 📱 Responsive Tasarım

### Breakpoints

```css
/* Tailwind default breakpoints */
sm: '640px',   /* Mobile landscape */
md: '768px',   /* Tablet */
lg: '1024px',  /* Laptop */
xl: '1280px',  /* Desktop */
2xl: '1536px', /* Large desktop */
```

### Responsive Grid

```tsx
// Mobile-first approach
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  <PriceCard />
  <PriceCard />
  <PriceCard />
  <PriceCard />
</div>
```

### Responsive Sidebar

```tsx
// Sidebar collapsible on mobile
<div className="flex">
  {/* Sidebar */}
  <aside className="hidden lg:block w-64 bg-gray-50">
    <Sidebar />
  </aside>
  
  {/* Mobile menu button */}
  <button className="lg:hidden" onClick={toggleMenu}>
    <MenuIcon />
  </button>
  
  {/* Main content */}
  <main className="flex-1">
    {children}
  </main>
</div>
```

### Mobile Navigation

```tsx
// Bottom navigation for mobile
<nav className="lg:hidden fixed bottom-0 inset-x-0 bg-white border-t">
  <div className="flex justify-around py-2">
    <NavItem icon={<HomeIcon />} label="Ana Sayfa" />
    <NavItem icon={<ChartIcon />} label="Piyasalar" />
    <NavItem icon={<BellIcon />} label="Bildirimler" />
    <NavItem icon={<UserIcon />} label="Profil" />
  </div>
</nav>
```

---

## ✨ Animasyonlar ve İnteraksiyonlar

### Loading States

```tsx
// Skeleton loader
<div className="animate-pulse">
  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
</div>

// Spinner
<div className="flex items-center justify-center">
  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
</div>
```

### Page Transitions

```tsx
// Using Framer Motion
import { motion } from 'framer-motion';

<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0, y: -20 }}
  transition={{ duration: 0.3 }}
>
  {children}
</motion.div>
```

### Hover Effects

```css
/* Tailwind utilities */
.card {
  @apply transition-all duration-200 hover:shadow-lg hover:-translate-y-1;
}

.button {
  @apply transition-colors duration-150 hover:bg-primary-600;
}
```

---

## 📊 Veri Görselleştirme

### Charts Library: Recharts

#### Line Chart (Price History)

```tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  { date: '2024-01', price: 2000 },
  { date: '2024-02', price: 2050 },
  // ...
];

<ResponsiveContainer width="100%" height={300}>
  <LineChart data={data}>
    <XAxis dataKey="date" />
    <YAxis />
    <Tooltip />
    <Line type="monotone" dataKey="price" stroke="#0ea5e9" strokeWidth={2} />
  </LineChart>
</ResponsiveContainer>
```

#### Bar Chart (Sentiment by Source)

```tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  { source: 'Twitter', sentiment: 70 },
  { source: 'Reddit', sentiment: 60 },
  { source: 'News', sentiment: 55 },
];

<ResponsiveContainer width="100%" height={300}>
  <BarChart data={data}>
    <XAxis dataKey="source" />
    <YAxis />
    <Tooltip />
    <Bar dataKey="sentiment" fill="#10b981" />
  </BarChart>
</ResponsiveContainer>
```

#### Pie Chart (Cost Breakdown)

```tsx
import { PieChart, Pie, Cell, ResponsiveContainer, Legend } from 'recharts';

const data = [
  { name: 'Cloud Run', value: 400 },
  { name: 'BigQuery', value: 300 },
  { name: 'Others', value: 300 },
];

const COLORS = ['#0ea5e9', '#10b981', '#f59e0b'];

<ResponsiveContainer width="100%" height={300}>
  <PieChart>
    <Pie
      data={data}
      cx="50%"
      cy="50%"
      labelLine={false}
      label
      outerRadius={80}
      fill="#8884d8"
      dataKey="value"
    >
      {data.map((entry, index) => (
        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
      ))}
    </Pie>
    <Legend />
  </PieChart>
</ResponsiveContainer>
```

---

## 🚀 Adım Adım Uygulama

### Adım 1: Proje Kurulumu

```bash
# Next.js projesi oluştur
npx create-next-app@latest sentilyze-web --typescript --tailwind --app

cd sentilyze-web

# Gerekli paketleri yükle
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu
npm install class-variance-authority clsx tailwind-merge
npm install recharts
npm install framer-motion
npm install lucide-react  # Icons
```

### Adım 2: shadcn/ui Kurulumu

```bash
npx shadcn-ui@latest init

# Components ekle
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add table
```

### Adım 3: Klasör Yapısı

```
sentilyze-web/
├── app/
│   ├── (marketing)/
│   │   ├── page.tsx          # Landing page
│   │   ├── about/
│   │   ├── pricing/
│   │   └── layout.tsx
│   ├── (dashboard)/
│   │   ├── altin/
│   │   │   ├── page.tsx      # Gold dashboard
│   │   │   └── analysis/
│   │   │       └── page.tsx
│   │   └── layout.tsx
│   ├── admin/
│   │   ├── page.tsx
│   │   └── feature-flags/
│   ├── api/
│   │   ├── gold/
│   │   ├── sentiment/
│   │   └── predictions/
│   ├── layout.tsx            # Root layout
│   └── globals.css
├── components/
│   ├── ui/                   # shadcn components
│   ├── dashboard/
│   │   ├── price-card.tsx
│   │   ├── sentiment-gauge.tsx
│   │   └── news-feed.tsx
│   ├── charts/
│   │   ├── line-chart.tsx
│   │   └── bar-chart.tsx
│   └── layout/
│       ├── navbar.tsx
│       ├── sidebar.tsx
│       └── footer.tsx
├── lib/
│   ├── utils.ts
│   ├── api.ts
│   └── feature-flags.tsx
├── types/
│   └── index.ts
└── public/
    ├── images/
    └── icons/
```

### Adım 4: Tema Konfigürasyonu

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        sentiment: {
          positive: '#10b981',
          negative: '#ef4444',
          neutral: '#6b7280',
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}

export default config
```

### Adım 5: API Integration

```typescript
// lib/api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export async function fetchGoldPrice() {
  const res = await fetch(`${API_BASE_URL}/api/gold/price?symbol=XAUUSD`);
  if (!res.ok) throw new Error('Failed to fetch gold price');
  return res.json();
}

export async function fetchSentiment(asset: string) {
  const res = await fetch(`${API_BASE_URL}/api/sentiment?asset=${asset}`);
  if (!res.ok) throw new Error('Failed to fetch sentiment');
  return res.json();
}
```

### Adım 6: İlk Sayfa - Landing Page

```tsx
// app/(marketing)/page.tsx
export default function LandingPage() {
  return (
    <>
      <HeroSection />
      <FeaturesSection />
      <HowItWorksSection />
      <LiveDemoSection />
      <PricingSection />
      <CTASection />
    </>
  );
}

// Hero Section
function HeroSection() {
  return (
    <section className="relative h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 text-center">
        <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
          Piyasa Duygusunu <span className="text-primary-600">Yapay Zeka</span> ile Oku
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          Kripto ve altın piyasalarındaki sentiment'i gerçek zamanlı analiz edin.
          Daha akıllı yatırım kararları alın.
        </p>
        <div className="flex gap-4 justify-center">
          <Button size="lg">Ücretsiz Dene</Button>
          <Button size="lg" variant="outline">Demo Gör</Button>
        </div>
      </div>
    </section>
  );
}
```

### Adım 7: Gold Dashboard Page

```tsx
// app/(dashboard)/altin/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { PriceCard } from '@/components/dashboard/price-card';
import { SentimentGauge } from '@/components/dashboard/sentiment-gauge';
import { PriceChart } from '@/components/charts/price-chart';
import { NewsFeed } from '@/components/dashboard/news-feed';

export default function GoldDashboard() {
  const [goldData, setGoldData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await fetchGoldPrice();
        setGoldData(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    
    // Polling every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <LoadingSkeleton />;

  return (
    <div className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold">Altın Piyasası</h1>
        <p className="text-gray-600">Son güncelleme: 2 dakika önce</p>
      </header>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <PriceCard asset="Altın" price={goldData.price} change24h={goldData.change24h} />
        <Card>
          <CardHeader>
            <CardTitle>24s Değişim</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{goldData.change24h}%</p>
          </CardContent>
        </Card>
        {/* More cards... */}
      </div>

      {/* Price Chart */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Fiyat Grafiği</CardTitle>
        </CardHeader>
        <CardContent>
          <PriceChart data={goldData.historicalPrices} />
        </CardContent>
      </Card>

      {/* Two columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sentiment */}
        <Card>
          <CardHeader>
            <CardTitle>Sentiment Skoru</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            <SentimentGauge score={goldData.sentimentScore} />
          </CardContent>
        </Card>

        {/* News Feed */}
        <Card>
          <CardHeader>
            <CardTitle>Son Haberler</CardTitle>
          </CardHeader>
          <CardContent>
            <NewsFeed items={goldData.news} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

### Adım 8: Dark Mode Implementasyonu

```tsx
// components/theme-provider.tsx
'use client';

import { ThemeProvider as NextThemesProvider } from 'next-themes';

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider attribute="class" defaultTheme="light">
      {children}
    </NextThemesProvider>
  );
}

// app/layout.tsx
import { ThemeProvider } from '@/components/theme-provider';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}

// Theme toggle button
import { useTheme } from 'next-themes';

function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
    >
      {theme === 'light' ? <MoonIcon /> : <SunIcon />}
    </Button>
  );
}
```

### Adım 9: Feature Flags Integration

```tsx
// lib/feature-flags.tsx
'use client';

import { createContext, useContext, useEffect, useState } from 'react';

interface FeatureFlags {
  ENABLE_GOLD_DATA: boolean;
  ENABLE_ML_PREDICTIONS: boolean;
  ENABLE_ADVANCED_ANALYTICS: boolean;
}

const FeatureFlagsContext = createContext<FeatureFlags>({} as FeatureFlags);

export function FeatureFlagsProvider({ children }: { children: React.ReactNode }) {
  const [flags, setFlags] = useState<FeatureFlags>({
    ENABLE_GOLD_DATA: true,
    ENABLE_ML_PREDICTIONS: false,
    ENABLE_ADVANCED_ANALYTICS: true,
  });

  useEffect(() => {
    // Fetch feature flags from API
    fetch('/api/feature-flags')
      .then(res => res.json())
      .then(data => setFlags(data))
      .catch(console.error);
  }, []);

  return (
    <FeatureFlagsContext.Provider value={flags}>
      {children}
    </FeatureFlagsContext.Provider>
  );
}

export function useFeatureFlags() {
  return useContext(FeatureFlagsContext);
}

// Usage
function GoldDashboard() {
  const flags = useFeatureFlags();

  if (!flags.ENABLE_GOLD_DATA) {
    return <ComingSoonMessage />;
  }

  return <ActualDashboard />;
}
```

### Adım 10: Deployment

```bash
# Build for production
npm run build

# Test production build locally
npm start

# Deploy to Vercel (recommended)
vercel --prod

# Or deploy to Google Cloud Run
# 1. Build Docker image
docker build -t sentilyze-web .

# 2. Push to Artifact Registry
docker tag sentilyze-web gcr.io/PROJECT_ID/sentilyze-web
docker push gcr.io/PROJECT_ID/sentilyze-web

# 3. Deploy to Cloud Run
gcloud run deploy sentilyze-web \
  --image gcr.io/PROJECT_ID/sentilyze-web \
  --platform managed \
  --region europe-west3 \
  --allow-unauthenticated
```

---

## 📚 Best Practices

### 1. Performance

- **Code Splitting**: Lazy load components
- **Image Optimization**: Use Next.js Image component
- **Caching**: Implement SWR or React Query
- **Bundle Size**: Monitor with `next/bundle-analyzer`

```tsx
// Lazy loading
import dynamic from 'next/dynamic';

const HeavyChart = dynamic(() => import('./heavy-chart'), {
  loading: () => <LoadingSkeleton />,
  ssr: false
});
```

### 2. Accessibility

- **Semantic HTML**: Use proper HTML tags
- **ARIA labels**: Add aria-labels to interactive elements
- **Keyboard Navigation**: Test with keyboard only
- **Color Contrast**: WCAG AA compliance

```tsx
<button
  aria-label="Close dialog"
  onClick={handleClose}
>
  <CloseIcon />
</button>
```

### 3. SEO

```tsx
// app/layout.tsx
export const metadata = {
  title: 'Sentilyze - Piyasa Sentiment Analizi',
  description: 'AI destekli kripto ve altın piyasası sentiment analizi',
  keywords: ['sentiment analizi', 'kripto', 'altın', 'ai', 'yatırım'],
};
```

### 4. Error Handling

```tsx
// app/error.tsx
'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h2 className="text-2xl font-bold mb-4">Bir hata oluştu</h2>
      <p className="text-gray-600 mb-4">{error.message}</p>
      <Button onClick={reset}>Tekrar Dene</Button>
    </div>
  );
}
```

---

## 🎯 Sonuç

Bu rehber, Sentilyze frontend'ini adım adım oluşturmak için gereken tüm bilgileri içermektedir:

1. ✅ Modern tech stack (Next.js, TypeScript, Tailwind)
2. ✅ Component-based architecture
3. ✅ Responsive design
4. ✅ Data visualization
5. ✅ Best practices

**Sonraki Adımlar**:
- Backend API endpoints'leri bağlayın
- Gerçek zamanlı veri akışı ekleyin
- Authentication implementasyonu
- Testing (Jest, React Testing Library)
- Analytics (Google Analytics, Mixpanel)

---

*Bu rehber Sentilyze frontend geliştirme için hazırlanmıştır.*
*Son güncelleme: Şubat 2026*

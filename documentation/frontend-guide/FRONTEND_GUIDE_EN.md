# Frontend UI Design Guide
## Sentilyze Web Platform

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Design Philosophy](#design-philosophy)
3. [Technology Stack](#technology-stack)
4. [Page Structures](#page-structures)
5. [Component Library](#component-library)
6. [Color Palette and Typography](#color-palette-and-typography)
7. [Responsive Design](#responsive-design)
8. [Animations and Interactions](#animations-and-interactions)
9. [Data Visualization](#data-visualization)
10. [Step-by-Step Implementation](#step-by-step-implementation)

---

## 🎯 Overview

The Sentilyze frontend is designed to provide a **modern, clean, and user-friendly** interface. Users should be able to easily understand complex financial data and navigate the platform comfortably.

### Target Users

1. **Individual Investors**: People tracking crypto and gold markets
2. **Professional Traders**: Experts seeking technical analysis and sentiment data
3. **Analysts**: Financial analysts conducting market research
4. **Enthusiasts**: People wanting to learn about market trends

### Platform Goals

- ✅ Simple and clear interface
- ✅ Fast data access
- ✅ Visually appealing charts
- ✅ Mobile-friendly design
- ✅ Accessible (accessibility)

---

## 🎨 Design Philosophy

### Core Principles

#### 1. **Clarity**
Every element should clearly show what it does. No ambiguity to confuse users.

#### 2. **Simplicity**
Minimal design. Avoid unnecessary elements. Each page should focus on a single purpose.

#### 3. **Consistency**
Use the same design language across all pages. Colors, fonts, and spacing should be consistent.

#### 4. **Hierarchy**
Information should be organized by priority. Most important information should be at the top and largest.

#### 5. **Feedback**
Users should receive feedback for every action (loading states, success messages, errors).

---

## 💻 Technology Stack

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

## 🏗️ Page Structures

### 1. Landing Page

**URL**: `/`

**Purpose**: Introduce platform, encourage user registration

**Sections**:

```
┌─────────────────────────────────────────────┐
│           NAVBAR (Sticky)                    │
├─────────────────────────────────────────────┤
│                                              │
│           HERO SECTION                       │
│  - Title: "Read Market Sentiment"          │
│  - Subtitle: Description                    │
│  - CTA Buttons: [Try Free] [See Demo]      │
│  - Hero Image/Animation                     │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           FEATURES SECTION                   │
│  Grid (3 columns)                           │
│  - AI-Powered Analysis                      │
│  - Real-time Data                           │
│  - Smart Alerts                             │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           HOW IT WORKS                       │
│  Timeline/Stepper (4 steps)                │
│  1. Data Collection                         │
│  2. AI Analysis                             │
│  3. Insight Generation                      │
│  4. Notification                            │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           LIVE DEMO SECTION                  │
│  - Sample sentiment chart                   │
│  - Real-time data feed                      │
│  - "See more" CTA                           │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           PRICING SECTION                    │
│  Cards (3 plans)                            │
│  - Free                                     │
│  - Professional                             │
│  - Enterprise                               │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           TESTIMONIALS                       │
│  Slider (user testimonials)                │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           CTA SECTION                        │
│  - "Start today" heading                    │
│  - Email signup form                        │
│                                              │
├─────────────────────────────────────────────┤
│                                              │
│           FOOTER                             │
│  - Links (About, Blog, Contact)             │
│  - Social media                             │
│  - Legal disclaimer                         │
│                                              │
└─────────────────────────────────────────────┘
```

---

### 2. Gold Dashboard

**URL**: `/altin` or `/gold`

**Purpose**: Real-time data and sentiment analysis about gold market

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
│  - Gold            │  │   Gold Market • Last Update       │ │
│  - Crypto          │  └───────────────────────────────────┘ │
│  - Settings        │                                         │
│  - Logout          │  ┌───────────────────────────────────┐ │
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
└────────────────────┴─────────────────────────────────────────┘
```

---

## 🎨 Component Library

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
    <CardTitle>Gold Price</CardTitle>
  </CardHeader>
  <CardContent>
    <p className="text-3xl font-bold">$2,045.50</p>
    <p className="text-green-600">+2.3%</p>
  </CardContent>
</Card>
```

### Custom Components

#### 1. SentimentGauge

**Usage**: Visually display sentiment score

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

#### 2. PriceCard

**Usage**: Price and change information card

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

---

## 🎨 Color Palette and Typography

### Color System

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

### Typography

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

---

## 📱 Responsive Design

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

---

## ✨ Animations and Interactions

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

---

## 📊 Data Visualization

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

---

## 🚀 Step-by-Step Implementation

### Step 1: Project Setup

```bash
# Create Next.js project
npx create-next-app@latest sentilyze-web --typescript --tailwind --app

cd sentilyze-web

# Install required packages
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu
npm install class-variance-authority clsx tailwind-merge
npm install recharts
npm install framer-motion
npm install lucide-react  # Icons
```

### Step 2: shadcn/ui Setup

```bash
npx shadcn-ui@latest init

# Add components
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add table
```

### Step 3: Folder Structure

```
sentilyze-web/
├── app/
│   ├── (marketing)/
│   │   ├── page.tsx          # Landing page
│   │   ├── about/
│   │   ├── pricing/
│   │   └── layout.tsx
│   ├── (dashboard)/
│   │   ├── gold/
│   │   │   ├── page.tsx      # Gold dashboard
│   │   │   └── analysis/
│   │   │       └── page.tsx
│   │   └── layout.tsx
│   ├── admin/
│   ├── api/
│   ├── layout.tsx            # Root layout
│   └── globals.css
├── components/
│   ├── ui/                   # shadcn components
│   ├── dashboard/
│   ├── charts/
│   └── layout/
├── lib/
├── types/
└── public/
```

### Step 4: Theme Configuration

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

### Step 5: API Integration

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

### Step 6: First Page - Landing Page

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
          Read Market Sentiment with <span className="text-primary-600">AI</span>
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          Analyze real-time sentiment in crypto and gold markets.
          Make smarter investment decisions.
        </p>
        <div className="flex gap-4 justify-center">
          <Button size="lg">Try Free</Button>
          <Button size="lg" variant="outline">See Demo</Button>
        </div>
      </div>
    </section>
  );
}
```

### Step 7: Gold Dashboard Page

```tsx
// app/(dashboard)/gold/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { PriceCard } from '@/components/dashboard/price-card';
import { SentimentGauge } from '@/components/dashboard/sentiment-gauge';

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
        <h1 className="text-3xl font-bold">Gold Market</h1>
        <p className="text-gray-600">Last update: 2 minutes ago</p>
      </header>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <PriceCard asset="Gold" price={goldData.price} change24h={goldData.change24h} />
        {/* More cards... */}
      </div>

      {/* Charts and more... */}
    </div>
  );
}
```

### Step 8: Dark Mode Implementation

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
```

### Step 9: Deployment

```bash
# Build for production
npm run build

# Test production build locally
npm start

# Deploy to Vercel (recommended)
vercel --prod

# Or deploy to Google Cloud Run
docker build -t sentilyze-web .
docker push gcr.io/PROJECT_ID/sentilyze-web
gcloud run deploy sentilyze-web --image gcr.io/PROJECT_ID/sentilyze-web
```

---

## 📚 Best Practices

### 1. Performance

- **Code Splitting**: Lazy load components
- **Image Optimization**: Use Next.js Image component
- **Caching**: Implement SWR or React Query
- **Bundle Size**: Monitor with `next/bundle-analyzer`

### 2. Accessibility

- **Semantic HTML**: Use proper HTML tags
- **ARIA labels**: Add aria-labels to interactive elements
- **Keyboard Navigation**: Test with keyboard only
- **Color Contrast**: WCAG AA compliance

### 3. SEO

```tsx
// app/layout.tsx
export const metadata = {
  title: 'Sentilyze - Market Sentiment Analysis',
  description: 'AI-powered crypto and gold market sentiment analysis',
  keywords: ['sentiment analysis', 'crypto', 'gold', 'ai', 'investment'],
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
      <h2 className="text-2xl font-bold mb-4">An error occurred</h2>
      <p className="text-gray-600 mb-4">{error.message}</p>
      <Button onClick={reset}>Try Again</Button>
    </div>
  );
}
```

---

## 🎯 Conclusion

This guide contains all the information needed to build the Sentilyze frontend step by step:

1. ✅ Modern tech stack (Next.js, TypeScript, Tailwind)
2. ✅ Component-based architecture
3. ✅ Responsive design
4. ✅ Data visualization
5. ✅ Best practices

**Next Steps**:
- Connect backend API endpoints
- Add real-time data streaming
- Authentication implementation
- Testing (Jest, React Testing Library)
- Analytics (Google Analytics, Mixpanel)

---

*This guide was prepared for Sentilyze frontend development.*
*Last updated: February 2026*

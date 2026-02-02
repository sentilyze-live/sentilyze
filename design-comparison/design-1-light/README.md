# Design 1: Açık Tema (Light Theme) - Mevcut apps/web

## Konum
`apps/web/` - Ana Next.js uygulaması

## Tema Özellikleri
- **Tema**: Açık tema (Light) - Beyaz/Grid arka plan
- **Renk Paleti**: 
  - Ana renk: Slate (Gri tonları)
  - Vurgu: Mavi (`blue-600`)
  - Arkaplan: Beyaz (`bg-slate-50`, `bg-white`)
- **Tipografi**: Inter font

## Klasör Yapısı
```
apps/web/
├── app/
│   ├── (marketing)/      # Marketing sayfaları
│   │   ├── page.tsx      # Landing page
│   │   ├── about/
│   │   ├── blog/
│   │   ├── contact/
│   │   ├── how-it-works/
│   │   ├── pricing/
│   │   └── product/
│   ├── (dashboard)/      # Dashboard sayfaları
│   │   └── altin/        # Altın analiz sayfası
│   ├── admin/            # Admin panel
│   └── api/              # API routes
├── components/
│   ├── ui/               # shadcn/ui bileşenleri
│   ├── marketing/        # Marketing bileşenleri
│   ├── dashboard/        # Dashboard bileşenleri
│   └── admin/            # Admin bileşenleri
└── lib/                  # Utils & hooks
```

## Öne Çıkan Özellikler
1. **Landing Page**: Hero section, problem/solution bölümleri
2. **Dashboard**: Altın fiyat takibi, sentiment analizi
3. **Admin Panel**: Feature flags yönetimi
4. **Marketing Pages**: About, Blog, Contact, Pricing, Product

## Teknoloji Stack
- Next.js 14+ (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui
- Lucide React (ikonlar)

## Karşılaştırma Notları
✅ Profesyonel kurumsal görünüm
✅ Modern UI/UX
✅ Dashboard ve marketing ayrımı
✅ Admin panel entegrasyonu
⚠️ Daha geleneksel finans uygulaması görünümü

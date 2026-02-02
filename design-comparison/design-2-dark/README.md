# Design 2: Koyu Tema (Dark Theme) - Bordo/Mavi UI Preview

## Konum
`ui-design-preview/index.html` - HTML Prototype

## Tema Özellikleri
- **Tema**: Koyu tema (Dark) - Bordo/Siyah arka plan
- **Renk Paleti**:
  - Ana renk: Bordo (`#4e0727`, `#2d0316`)
  - Vurgu: Gökyüzü mavisi (`#82c8fc`)
  - Arkaplan: Koyu bordo gradient
- **Tipografi**: Inter font

## Özel CSS Özellikleri
```css
.gradient-bg {
    background: linear-gradient(135deg, #2d0316 0%, #4e0727 50%, #2d0316 100%);
}
.card-gradient {
    background: linear-gradient(145deg, rgba(78, 7, 39, 0.8) 0%, rgba(45, 3, 22, 0.9) 100%);
}
.glow-sky {
    box-shadow: 0 0 20px rgba(130, 200, 252, 0.3);
}
```

## Bölümler
1. **Navigation**: Yapışkan header, bordo arka plan
2. **Hero Section**: Gradient arka plan, büyük başlık
3. **Dashboard Preview**: Stats grid (Fiyat, Sentiment, Tahmin)
4. **AI Analysis Card**: Etkileşimli analiz kartı
5. **Feature Highlights**: 3 özellik kartı
6. **Color Palette**: Renk referansları
7. **Typography**: Tipografi örnekleri
8. **Button Variants**: Farklı buton stilleri

## Öne Çıkan Özellikler
1. **Premium/Gaming Vibe**: Bordo + Mavi kombinasyonu
2. **Glassmorphism**: Yarı saydam kartlar (`backdrop-blur`)
3. **Glow Efektleri**: Mavi ışık efektleri
4. **Live Price Simulation**: Gerçek zamanlı fiyat animasyonu

## Teknoloji Stack
- HTML5
- Tailwind CSS (CDN)
- Lucide Icons (CDN)
- Vanilla JavaScript

## Karşılaştırma Notları
✅ Benzersiz, dikkat çekici tasarım
✅ Kripto/fintech uyumu (koyu tema trendi)
✅ Premium hissi
✅ Modern gradient ve blur efektleri
⚠️ Geleneksel kurumsal algıdan uzak
⚠️ HTML prototype, Next.js'e dönüştürülmesi gerekli

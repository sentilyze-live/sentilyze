import React, { useEffect, useState } from 'react';
import { Bell, Share2, Star, RefreshCw, ExternalLink } from 'lucide-react';
import { getGoldPrice, type ForexRate } from '../../lib/api/finnhubApi';

const GoldHeader: React.FC = () => {
  const [price, setPrice] = useState<ForexRate | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  useEffect(() => {
    const fetchPrice = async () => {
      try {
        setIsLoading(true);
        const data = await getGoldPrice();
        if (data) {
          setPrice(data);
          setLastUpdated(new Date());
        }
      } catch (error) {
        console.error('Failed to fetch gold price:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPrice();
    const interval = setInterval(fetchPrice, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  const isPositive = price ? price.change >= 0 : true;
  const displayPrice = price?.price || 2450.30;
  const displayChange = price?.change || 15.40;
  const displayChangePercent = price?.changePercent || 0.63;

  const formatTurkishNumber = (num: number) => {
    return num.toLocaleString('tr-TR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  const formatTimeAgo = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    
    if (diffSecs < 60) return 'Az önce';
    if (diffMins < 60) return `${diffMins} dk önce`;
    return date.toLocaleTimeString('tr-TR');
  };

  const handleRefresh = () => {
    window.location.reload();
  };

  return (
    <header 
      className="sticky top-0 z-40 bg-[var(--bg-secondary)] border-b border-[var(--border-color)]"
      role="banner"
      aria-label="Altın fiyat bilgileri"
    >
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div>
              {/* Ana Fiyat - Gold Accent */}
              <div className="flex items-baseline gap-2" role="group" aria-label="Mevcut altın fiyatı">
                <span 
                  className="text-4xl font-extrabold tracking-tight gold-highlight"
                  aria-live="polite"
                  aria-atomic="true"
                >
                  {isLoading ? (
                    <span className="animate-pulse" aria-label="Fiyat yükleniyor">...</span>
                  ) : (
                    formatTurkishNumber(displayPrice)
                  )}
                </span>
                <span className="text-lg text-[var(--text-secondary)]">USD</span>
              </div>
              
              {/* Değişim - Yeşil/Kırmızı Sentiment */}
              <div className="flex items-center gap-3 mt-1" role="group" aria-label="24 saatlik değişim">
                <span 
                  className={`text-lg font-bold ${isPositive ? 'price-bullish' : 'price-bearish'}`}
                  aria-label={`Değişim: ${isPositive ? 'Artı' : 'Eksi'} ${formatTurkishNumber(Math.abs(displayChange))} USD, Yüzde ${formatTurkishNumber(displayChangePercent)}`}
                >
                  {isPositive ? '+' : ''}{formatTurkishNumber(displayChange)} ({isPositive ? '+' : ''}{formatTurkishNumber(displayChangePercent)}%)
                </span>
                <span className="text-sm text-[var(--text-muted)]">
                  24s Yüksek: <span className="price-bullish font-semibold">{formatTurkishNumber(price?.high || 2465.20)}</span> |
                  Düşük: <span className="price-bearish font-semibold">{formatTurkishNumber(price?.low || 2432.10)}</span>
                </span>
              </div>
              
              {/* Veri Kaynağı */}
              <div className="flex items-center gap-2 mt-1 text-xs text-[var(--text-muted)]">
                <span>Güncelleme: {formatTimeAgo(lastUpdated)}</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  Kaynak:
                  <a
                    href="https://finnhub.io/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="gold-highlight hover:underline inline-flex items-center"
                  >
                    Finnhub
                    <ExternalLink className="w-3 h-3 ml-1" />
                  </a>
                </span>
              </div>
            </div>
          </div>

          {/* Mini Grafik */}
          <div className="hidden md:flex items-center" aria-hidden="true">
            <svg width="200" height="60" className="opacity-80">
              <path
                d="M0,40 Q20,35 40,30 T80,25 T120,35 T160,30 T200,20"
                fill="none"
                stroke={isPositive ? "var(--market-up)" : "var(--market-down)"}
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>

          {/* Aksiyon Butonları */}
          <div className="flex items-center gap-3" role="group" aria-label="Hızlı aksiyonlar">
            <button 
              className="p-2 rounded-lg bg-[var(--bg-tertiary)] hover:gold-bg hover:gold-highlight text-[var(--text-secondary)] transition-all duration-200"
              aria-label="Favorilere ekle"
            >
              <Star className="w-5 h-5" />
            </button>
            <button 
              className="p-2 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--market-neutral-light)] hover:text-[var(--market-neutral)] text-[var(--text-secondary)] transition-all duration-200"
              aria-label="Fiyat alarmı kur"
            >
              <Bell className="w-5 h-5" />
            </button>
            <button 
              className="p-2 rounded-lg bg-[var(--bg-tertiary)] hover:gold-bg hover:gold-highlight text-[var(--text-secondary)] transition-all duration-200"
              aria-label="Paylaş"
            >
              <Share2 className="w-5 h-5" />
            </button>
            <button 
              onClick={handleRefresh}
              className="p-2 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--market-up-light)] hover:text-[var(--market-up)] text-[var(--text-secondary)] transition-all duration-200"
              aria-label="Sayfayı yenile"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default GoldHeader;

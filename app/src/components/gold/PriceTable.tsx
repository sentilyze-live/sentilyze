import React, { useEffect, useState } from 'react';
import { getAllPrices, type ForexRate } from '../../lib/api/finnhubApi';
import { TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';

interface PriceCardProps {
  title: string;
  subtitle: string;
  buyPrice: number | null;
  sellPrice: number | null;
  change: number | null;
  changePercent: number | null;
  isLoading: boolean;
}

const PriceCard: React.FC<PriceCardProps> = ({
  title,
  subtitle,
  buyPrice,
  sellPrice,
  change,
  changePercent,
  isLoading,
}) => {
  const isPositive = (change || 0) >= 0;
  const displayBuy = buyPrice?.toFixed(2) || '---';
  const displaySell = sellPrice?.toFixed(2) || '---';

  return (
    <div className="risk-card p-4 hover:shadow-lg transition-shadow duration-300">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wide">
            {title}
          </h3>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">{subtitle}</p>
        </div>
        {changePercent !== null && (
          <div className={`flex items-center gap-1 px-2 py-1 rounded-full ${
            isPositive ? 'bg-[var(--market-up-light)]' : 'bg-[var(--market-down-light)]'
          }`}>
            {isPositive ? (
              <TrendingUp className={`w-3 h-3 price-bullish`} />
            ) : (
              <TrendingDown className={`w-3 h-3 price-bearish`} />
            )}
            <span className={`text-xs font-bold ${isPositive ? 'price-bullish' : 'price-bearish'}`}>
              {isPositive ? '+' : ''}{changePercent.toFixed(2)}%
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-[var(--bg-tertiary)] rounded-lg p-3">
          <p className="text-xs text-[var(--text-muted)] mb-1 font-medium">Alış</p>
          {isLoading ? (
            <div className="h-7 bg-[var(--bg-hover)] animate-pulse rounded"></div>
          ) : (
            <p className="text-xl font-bold price-bullish font-mono">{displayBuy}</p>
          )}
        </div>
        <div className="bg-[var(--bg-tertiary)] rounded-lg p-3">
          <p className="text-xs text-[var(--text-muted)] mb-1 font-medium">Satış</p>
          {isLoading ? (
            <div className="h-7 bg-[var(--bg-hover)] animate-pulse rounded"></div>
          ) : (
            <p className="text-xl font-bold price-bearish font-mono">{displaySell}</p>
          )}
        </div>
      </div>
    </div>
  );
};

const PriceTable: React.FC = () => {
  const [prices, setPrices] = useState<{
    gold: ForexRate | null;
    usdtry: ForexRate | null;
    eurtry: ForexRate | null;
  }>({
    gold: null,
    usdtry: null,
    eurtry: null,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchPrices = async () => {
    try {
      setIsLoading(true);
      const data = await getAllPrices();
      setPrices(data);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to fetch prices:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPrices();
    const interval = setInterval(fetchPrices, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchPrices();
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

  // Calculate gram gold price from ounce (1 oz = 31.1035 gram)
  const gramGoldPrice = prices.gold && prices.usdtry
    ? (prices.gold.price / 31.1035) * prices.usdtry.price
    : null;

  const gramGoldBuy = gramGoldPrice ? gramGoldPrice * 0.995 : null;
  const gramGoldSell = gramGoldPrice ? gramGoldPrice * 1.005 : null;

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[var(--gold-primary)] to-[var(--gold-soft)] flex items-center justify-center">
            <span className="text-xl">💰</span>
          </div>
          <div>
            <h2 className="text-2xl font-bold text-[var(--text-primary)]">
              Canlı Fiyatlar
            </h2>
            <p className="text-sm text-[var(--text-muted)]">
              Son güncelleme: {formatTimeAgo(lastUpdated)}
            </p>
          </div>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className={`p-2.5 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--gold-light)] hover:text-[var(--gold-primary)] text-[var(--text-secondary)] transition-all duration-200 ${
            isRefreshing ? 'animate-spin' : ''
          }`}
          aria-label="Fiyatları yenile"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      <div className="flex flex-col gap-4">
        <PriceCard
          title="Altın (Gram)"
          subtitle="TL Bazlı"
          buyPrice={gramGoldBuy}
          sellPrice={gramGoldSell}
          change={prices.gold?.change || null}
          changePercent={prices.gold?.changePercent || null}
          isLoading={isLoading}
        />

        <PriceCard
          title="Ons Altın"
          subtitle="XAU/USD"
          buyPrice={prices.gold ? prices.gold.price * 0.998 : null}
          sellPrice={prices.gold ? prices.gold.price * 1.002 : null}
          change={prices.gold?.change || null}
          changePercent={prices.gold?.changePercent || null}
          isLoading={isLoading}
        />

        <PriceCard
          title="USD/TL"
          subtitle="Amerikan Doları"
          buyPrice={prices.usdtry ? prices.usdtry.price * 0.999 : null}
          sellPrice={prices.usdtry ? prices.usdtry.price * 1.001 : null}
          change={prices.usdtry?.change || null}
          changePercent={prices.usdtry?.changePercent || null}
          isLoading={isLoading}
        />

        <PriceCard
          title="EUR/TL"
          subtitle="Euro"
          buyPrice={prices.eurtry ? prices.eurtry.price * 0.999 : null}
          sellPrice={prices.eurtry ? prices.eurtry.price * 1.001 : null}
          change={prices.eurtry?.change || null}
          changePercent={prices.eurtry?.changePercent || null}
          isLoading={isLoading}
        />
      </div>

      <div className="mt-4 p-3 bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-lg">
        <div className="flex items-start gap-2 text-xs text-[var(--text-muted)]">
          <span className="text-yellow-500">⚠️</span>
          <p>
            <strong className="text-[var(--text-secondary)]">Yasal Uyarı:</strong> Bu fiyatlar yalnızca bilgi amaçlıdır ve yatırım tavsiyesi niteliği taşımaz.
            Gerçek işlem fiyatları piyasa koşullarına göre değişiklik gösterebilir. Finnhub API kullanılarak sağlanmaktadır.
          </p>
        </div>
      </div>
    </div>
  );
};

export default PriceTable;

import React, { useEffect } from 'react';
import { TrendingUp, TrendingDown, Minus, Activity, DollarSign, Percent, AlertTriangle } from 'lucide-react';
import { useGoldStore, useMarketContext } from '../../stores/goldStore';

const MarketContext: React.FC = () => {
  const context = useMarketContext();
  const { fetchContext, isLoadingContext, errorContext } = useGoldStore();

  useEffect(() => {
    fetchContext();
  }, []);

  if (isLoadingContext) {
    return (
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-white/40 rounded-2xl p-6 shadow-2xl">
        <div className="animate-pulse">
          <div className="h-6 bg-white/10 rounded w-1/2 mb-4"></div>
          <div className="space-y-3">
            <div className="h-16 bg-white/10 rounded"></div>
            <div className="h-16 bg-white/10 rounded"></div>
            <div className="h-24 bg-white/10 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (errorContext) {
    return (
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-red-500/40 rounded-2xl p-6 shadow-2xl">
        <h3 className="text-lg font-bold text-white mb-2">Piyasa Bağlamı</h3>
        <p className="text-red-400 text-sm">{errorContext}</p>
      </div>
    );
  }

  if (!context) {
    return (
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-white/40 rounded-2xl p-6 shadow-2xl">
        <h3 className="text-lg font-bold text-white mb-2">Piyasa Bağlamı</h3>
        <p className="text-gray-400 text-sm">Veri yükleniyor...</p>
      </div>
    );
  }

  const getRegimeColor = (regime: string) => {
    if (regime === 'bullish') return 'from-green-500 to-emerald-500';
    if (regime === 'bearish') return 'from-red-500 to-rose-500';
    return 'from-gray-500 to-slate-500';
  };

  const getRegimeIcon = (regime: string) => {
    if (regime === 'bullish') return <TrendingUp className="w-6 h-6" />;
    if (regime === 'bearish') return <TrendingDown className="w-6 h-6" />;
    return <Minus className="w-6 h-6" />;
  };

  const getRegimeText = (regime: string) => {
    if (regime === 'bullish') return 'Yükseliş';
    if (regime === 'bearish') return 'Düşüş';
    return 'Yatay';
  };

  const getTrendIcon = (direction: string) => {
    if (direction === 'up') return <TrendingUp className="w-5 h-5 text-green-400" />;
    if (direction === 'down') return <TrendingDown className="w-5 h-5 text-red-400" />;
    return <Minus className="w-5 h-5 text-gray-400" />;
  };

  const getVolatilityColor = (regime: string) => {
    if (regime === 'high') return 'text-red-400 bg-red-500/20';
    if (regime === 'normal') return 'text-yellow-400 bg-yellow-500/20';
    return 'text-green-400 bg-green-500/20';
  };

  const getFactorColor = (value: number) => {
    if (value > 0.7) return 'text-green-400';
    if (value < 0.3) return 'text-red-400';
    return 'text-yellow-400';
  };

  return (
    <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-white/40 rounded-2xl p-6 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center shadow-lg">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Piyasa Bağlamı</h3>
            <p className="text-xs text-gray-400">{context.symbol}</p>
          </div>
        </div>
      </div>

      {/* Market Regime */}
      <div className={`bg-gradient-to-r ${getRegimeColor(context.regime)} rounded-xl p-4 mb-4`}>
        <div className="flex items-center justify-between text-white">
          <div className="flex items-center gap-3">
            {getRegimeIcon(context.regime)}
            <div>
              <p className="text-sm opacity-90">Piyasa Rejimi</p>
              <p className="text-xl font-bold">{getRegimeText(context.regime)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Trend & Volatility */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-[var(--bg-tertiary)]/60 rounded-xl p-4 border border-white/20">
          <div className="flex items-center gap-2 mb-2">
            {getTrendIcon(context.trend.direction)}
            <p className="text-sm text-gray-300">Trend</p>
          </div>
          <p className="text-lg font-bold text-white capitalize">{context.trend.direction}</p>
          <div className="mt-2 w-full bg-white/10 rounded-full h-1.5">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full"
              style={{ width: `${context.trend.strength * 100}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 mt-1">Güç: {(context.trend.strength * 100).toFixed(0)}%</p>
        </div>

        <div className="bg-[var(--bg-tertiary)]/60 rounded-xl p-4 border border-white/20">
          <p className="text-sm text-gray-300 mb-2">Volatilite</p>
          <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full ${getVolatilityColor(context.volatility.regime)}`}>
            <Activity className="w-4 h-4" />
            <span className="text-sm font-semibold capitalize">{context.volatility.regime}</span>
          </div>
          <p className="text-xs text-gray-400 mt-2">Değer: {context.volatility.value.toFixed(2)}</p>
        </div>
      </div>

      {/* Support & Resistance Levels */}
      <div className="bg-[var(--bg-tertiary)]/60 rounded-xl p-4 border border-white/20 mb-4">
        <p className="text-sm text-gray-300 mb-3 font-semibold">Teknik Seviyeler</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-gray-400 mb-2">Destek</p>
            <div className="space-y-1">
              {context.levels.support.slice(0, 3).map((level, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500"></div>
                  <p className="text-sm text-white">₺{level.toFixed(2)}</p>
                </div>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-2">Direnç</p>
            <div className="space-y-1">
              {context.levels.resistance.slice(0, 3).map((level, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-red-500"></div>
                  <p className="text-sm text-white">₺{level.toFixed(2)}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Market Factors */}
      <div className="space-y-2">
        <p className="text-sm text-gray-300 font-semibold mb-3">Piyasa Faktörleri</p>

        <div className="flex items-center justify-between bg-[var(--bg-tertiary)]/40 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-300">USD Gücü</span>
          </div>
          <span className={`text-sm font-semibold ${getFactorColor(context.factors.usd_strength)}`}>
            {(context.factors.usd_strength * 100).toFixed(0)}%
          </span>
        </div>

        <div className="flex items-center justify-between bg-[var(--bg-tertiary)]/40 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <Percent className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-300">Faiz Oranları</span>
          </div>
          <span className={`text-sm font-semibold ${getFactorColor(context.factors.interest_rates)}`}>
            {(context.factors.interest_rates * 100).toFixed(0)}%
          </span>
        </div>

        <div className="flex items-center justify-between bg-[var(--bg-tertiary)]/40 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-300">Jeopolitik Risk</span>
          </div>
          <span className={`text-sm font-semibold ${getFactorColor(context.factors.geopolitical_risk)}`}>
            {(context.factors.geopolitical_risk * 100).toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  );
};

export default MarketContext;

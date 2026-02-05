import React, { useEffect, useState } from 'react';
import { GitCompare, TrendingUp, TrendingDown } from 'lucide-react';
import { useGoldStore, useCorrelationDetails } from '../../stores/goldStore';

const CorrelationMatrix: React.FC = () => {
  const correlationDetails = useCorrelationDetails();
  const { fetchCorrelationDetails, isLoadingCorrelationDetails, errorCorrelationDetails } = useGoldStore();
  const [selectedPeriod, setSelectedPeriod] = useState<number>(30);

  useEffect(() => {
    fetchCorrelationDetails(['DXY', 'SPX', 'US10Y'], selectedPeriod);
  }, [selectedPeriod]);

  if (isLoadingCorrelationDetails) {
    return (
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-white/40 rounded-2xl p-6 shadow-2xl">
        <div className="animate-pulse">
          <div className="h-6 bg-white/10 rounded w-1/2 mb-4"></div>
          <div className="space-y-3">
            <div className="h-24 bg-white/10 rounded"></div>
            <div className="h-24 bg-white/10 rounded"></div>
            <div className="h-24 bg-white/10 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (errorCorrelationDetails) {
    return (
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-red-500/40 rounded-2xl p-6 shadow-2xl">
        <h3 className="text-lg font-bold text-white mb-2">Korelasyon Analizi</h3>
        <p className="text-red-400 text-sm">{errorCorrelationDetails}</p>
      </div>
    );
  }

  if (!correlationDetails) {
    return (
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-white/40 rounded-2xl p-6 shadow-2xl">
        <h3 className="text-lg font-bold text-white mb-2">Korelasyon Analizi</h3>
        <p className="text-gray-400 text-sm">Veri yükleniyor...</p>
      </div>
    );
  }

  const getCorrelationColor = (correlation: number) => {
    const absCorr = Math.abs(correlation);
    if (absCorr > 0.7) return correlation > 0 ? 'from-green-600 to-green-400' : 'from-red-600 to-red-400';
    if (absCorr > 0.4) return correlation > 0 ? 'from-green-500 to-green-300' : 'from-red-500 to-red-300';
    return 'from-gray-500 to-gray-400';
  };

  const getCorrelationBgColor = (correlation: number) => {
    const absCorr = Math.abs(correlation);
    if (absCorr > 0.7) return correlation > 0 ? 'bg-green-500/20' : 'bg-red-500/20';
    if (absCorr > 0.4) return correlation > 0 ? 'bg-green-500/10' : 'bg-red-500/10';
    return 'bg-gray-500/10';
  };

  const getStrengthText = (strength: string) => {
    if (strength === 'strong') return 'Güçlü';
    if (strength === 'moderate') return 'Orta';
    return 'Zayıf';
  };

  const getDirectionIcon = (direction: string) => {
    if (direction === 'positive') return <TrendingUp className="w-4 h-4 text-green-400" />;
    return <TrendingDown className="w-4 h-4 text-red-400" />;
  };

  const getAssetName = (symbol: string) => {
    const names: Record<string, string> = {
      'DXY': 'Dolar Endeksi',
      'SPX': 'S&P 500',
      'US10Y': '10 Yıllık Tahvil'
    };
    return names[symbol] || symbol;
  };

  const periods = [7, 30, 90];

  return (
    <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-white/40 rounded-2xl p-6 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center shadow-lg">
            <GitCompare className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Korelasyon Analizi</h3>
            <p className="text-xs text-gray-400">Çapraz Varlık İlişkileri</p>
          </div>
        </div>
      </div>

      {/* Period Selector */}
      <div className="flex gap-2 mb-6">
        {periods.map((period) => (
          <button
            key={period}
            onClick={() => setSelectedPeriod(period)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              period === selectedPeriod
                ? 'bg-[var(--gold-primary)] text-black'
                : 'bg-white/10 text-gray-300 hover:bg-white/20'
            }`}
          >
            {period}d
          </button>
        ))}
      </div>

      {/* Correlation Cards */}
      <div className="space-y-4">
        {Object.entries(correlationDetails).map(([symbol, detail]) => (
          <div
            key={symbol}
            className={`${getCorrelationBgColor(detail.correlation)} rounded-xl p-4 border border-white/20 hover:border-white/40 transition-all`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                {getDirectionIcon(detail.direction)}
                <div>
                  <p className="text-white font-semibold">{symbol}</p>
                  <p className="text-xs text-gray-400">{getAssetName(symbol)}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-white">
                  {detail.correlation > 0 ? '+' : ''}{(detail.correlation * 100).toFixed(0)}%
                </p>
                <p className="text-xs text-gray-400">{getStrengthText(detail.strength)}</p>
              </div>
            </div>

            {/* Correlation Bar */}
            <div className="w-full bg-white/10 rounded-full h-3 overflow-hidden mb-3">
              <div
                className={`h-full bg-gradient-to-r ${getCorrelationColor(detail.correlation)} transition-all duration-500`}
                style={{
                  width: `${Math.abs(detail.correlation) * 100}%`,
                  marginLeft: detail.correlation < 0 ? `${100 - Math.abs(detail.correlation) * 100}%` : '0'
                }}
              />
            </div>

            {/* Interpretation */}
            <p className="text-xs text-gray-300 leading-relaxed">
              {detail.interpretation}
            </p>
          </div>
        ))}
      </div>

      {/* Footer Info */}
      <div className="mt-6 pt-4 border-t border-white/10">
        <div className="flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span>Pozitif</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span>Negatif</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-gray-500"></div>
              <span>Nötr</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CorrelationMatrix;

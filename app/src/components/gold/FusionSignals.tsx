import React, { useState, useEffect, useCallback } from 'react';
import { TrendingUp, TrendingDown, Minus, AlertTriangle, RefreshCw, Clock, Target, BarChart3, Zap, ChevronRight } from 'lucide-react';
import {
  getScalpingFusionSignal,
  getIntradayFusionSignal,
  getSwingFusionSignal,
  type FusionSignal
} from '../../lib/api/realApi';

type Strategy = 'scalping' | 'intraday' | 'swing';

const strategyInfo: Record<Strategy, { label: string; timeframe: string; description: string; icon: string }> = {
  scalping: {
    label: 'Scalping',
    timeframe: '5-15 dk',
    description: 'RSI + Bollinger + Twitter',
    icon: 'Zap'
  },
  intraday: {
    label: 'Intraday',
    timeframe: '1-4 saat',
    description: 'MACD + EMA + Haberler',
    icon: 'Clock'
  },
  swing: {
    label: 'Swing',
    timeframe: 'Günlük',
    description: 'Trend + Forum Sentiment',
    icon: 'TrendingUp'
  }
};

const FusionSignals: React.FC = () => {
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy>('intraday');
  const [signal, setSignal] = useState<FusionSignal | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [showFactors, setShowFactors] = useState(false);

  const fetchSignal = useCallback(async () => {
    setLoading(true);
    try {
      let result: FusionSignal | null = null;

      switch (selectedStrategy) {
        case 'scalping':
          result = await getScalpingFusionSignal();
          break;
        case 'intraday':
          result = await getIntradayFusionSignal();
          break;
        case 'swing':
          result = await getSwingFusionSignal();
          break;
      }

      setSignal(result);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Fusion signal fetch error:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedStrategy]);

  useEffect(() => {
    fetchSignal();

    const intervals: Record<Strategy, number> = {
      scalping: 30000,
      intraday: 60000,
      swing: 300000
    };

    const interval = setInterval(fetchSignal, intervals[selectedStrategy]);
    return () => clearInterval(interval);
  }, [selectedStrategy, fetchSignal]);

  const getSignalConfig = (signalType: string) => {
    switch (signalType) {
      case 'BUY':
        return {
          label: 'Yükseliş Potansiyeli Sinyali',
          sublabel: 'Teknik Göstergeler Pozitif',
          color: 'from-green-500 to-emerald-600',
          bgColor: 'bg-green-500/10',
          borderColor: 'border-green-500/30',
          textColor: 'text-green-400',
          icon: TrendingUp,
          pulse: 'animate-pulse'
        };
      case 'SELL':
        return {
          label: 'Düşüş Riski Sinyali',
          sublabel: 'Dikkatli Takip Önerilir',
          color: 'from-red-500 to-rose-600',
          bgColor: 'bg-red-500/10',
          borderColor: 'border-red-500/30',
          textColor: 'text-red-400',
          icon: TrendingDown,
          pulse: 'animate-pulse'
        };
      default:
        return {
          label: 'Nötr Piyasa Görünümü',
          sublabel: 'Karışık Sinyaller',
          color: 'from-yellow-500 to-amber-600',
          bgColor: 'bg-yellow-500/10',
          borderColor: 'border-yellow-500/30',
          textColor: 'text-yellow-400',
          icon: Minus,
          pulse: ''
        };
    }
  };

  const getConfidenceGradient = (confidence: number) => {
    if (confidence >= 75) return 'from-green-500 to-emerald-400';
    if (confidence >= 50) return 'from-yellow-500 to-amber-400';
    return 'from-red-500 to-rose-400';
  };

  return (
    <div className="terminal-card p-5 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/20">
            <Target className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Birleşik Gösterge</h3>
            <p className="text-[10px] text-gray-500">AI Model + Teknik Analiz + Duygu Skoru</p>
          </div>
        </div>

        <button
          onClick={fetchSignal}
          disabled={loading}
          className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-all hover:scale-105"
        >
          <RefreshCw className={`w-4 h-4 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Strategy Tabs */}
      <div className="flex gap-1 p-1 mb-4 bg-black/20 rounded-xl">
        {(Object.keys(strategyInfo) as Strategy[]).map((strategy) => (
          <button
            key={strategy}
            onClick={() => setSelectedStrategy(strategy)}
            className={`flex-1 py-2 px-2 rounded-lg text-xs font-medium transition-all ${
              selectedStrategy === strategy
                ? 'bg-gradient-to-r from-amber-500/30 to-orange-500/30 text-amber-300 shadow-lg shadow-amber-500/10'
                : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
            }`}
          >
            <div className="font-semibold">{strategyInfo[strategy].label}</div>
            <div className="text-[10px] opacity-70 mt-0.5">{strategyInfo[strategy].timeframe}</div>
          </button>
        ))}
      </div>

      {/* Loading */}
      {loading && !signal && (
        <div className="flex-1 flex items-center justify-center">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-amber-500/20 rounded-full"></div>
            <div className="absolute top-0 left-0 w-16 h-16 border-4 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
          </div>
        </div>
      )}

      {/* Signal Display */}
      {signal && (
        <div className="flex-1 flex flex-col">
          {/* Big Signal Card */}
          {(() => {
            const config = getSignalConfig(signal.signal);
            const IconComponent = config.icon;
            return (
              <div className={`relative overflow-hidden rounded-2xl ${config.bgColor} border ${config.borderColor} p-4 mb-4`}>
                {/* Background Glow */}
                <div className={`absolute -top-10 -right-10 w-32 h-32 bg-gradient-to-br ${config.color} opacity-20 blur-3xl rounded-full`}></div>

                <div className="relative flex items-center justify-between">
                  {/* Signal Info */}
                  <div className="flex items-center gap-3">
                    <div className={`p-3 rounded-xl bg-gradient-to-br ${config.color} shadow-lg ${config.pulse}`}>
                      <IconComponent className="w-7 h-7 text-white" />
                    </div>
                    <div>
                      <div className={`text-2xl font-black ${config.textColor}`}>
                        {config.label}
                      </div>
                      <div className="text-xs text-gray-400">{config.sublabel}</div>
                    </div>
                  </div>

                  {/* Confidence Ring */}
                  <div className="relative w-16 h-16">
                    <svg className="w-16 h-16 transform -rotate-90">
                      <circle
                        cx="32"
                        cy="32"
                        r="28"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="transparent"
                        className="text-gray-700"
                      />
                      <circle
                        cx="32"
                        cy="32"
                        r="28"
                        stroke="url(#confidenceGradient)"
                        strokeWidth="4"
                        fill="transparent"
                        strokeLinecap="round"
                        strokeDasharray={`${(signal.confidence / 100) * 176} 176`}
                        className="transition-all duration-1000"
                      />
                      <defs>
                        <linearGradient id="confidenceGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor={signal.confidence >= 75 ? '#22c55e' : signal.confidence >= 50 ? '#eab308' : '#ef4444'} />
                          <stop offset="100%" stopColor={signal.confidence >= 75 ? '#10b981' : signal.confidence >= 50 ? '#f59e0b' : '#f87171'} />
                        </linearGradient>
                      </defs>
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className={`text-lg font-bold ${signal.confidence >= 75 ? 'text-green-400' : signal.confidence >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                        {signal.confidence.toFixed(0)}
                      </span>
                      <span className="text-[8px] text-gray-500">GVN</span>
                    </div>
                  </div>
                </div>

                {/* Score Bar */}
                <div className="mt-4 pt-3 border-t border-white/10">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-gray-500">Birleşik Skor</span>
                    <span className={`font-mono font-bold ${signal.combined_score > 0 ? 'text-green-400' : signal.combined_score < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                      {signal.combined_score > 0 ? '+' : ''}{signal.combined_score.toFixed(3)}
                    </span>
                  </div>
                  <div className="h-2 bg-black/30 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 bg-gradient-to-r ${getConfidenceGradient(signal.confidence)}`}
                      style={{ width: `${Math.abs(signal.combined_score) * 50 + 50}%`, marginLeft: signal.combined_score < 0 ? `${50 - Math.abs(signal.combined_score) * 50}%` : '50%' }}
                    ></div>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Divergence Alert */}
          {signal.divergence_alert && signal.divergence_message && (
            <div className="mb-4 p-3 rounded-xl bg-orange-500/10 border border-orange-500/30 animate-pulse">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-orange-400 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-semibold text-orange-400">Uyumsuzluk Tespit Edildi</div>
                  <div className="text-[11px] text-gray-400 mt-1 leading-relaxed">{signal.divergence_message}</div>
                </div>
              </div>
            </div>
          )}

          {/* Expandable Factors */}
          <button
            onClick={() => setShowFactors(!showFactors)}
            className="flex items-center justify-between w-full p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors mb-3"
          >
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-gray-500" />
              <span className="text-xs text-gray-400">Faktör Detayları</span>
            </div>
            <ChevronRight className={`w-4 h-4 text-gray-500 transition-transform ${showFactors ? 'rotate-90' : ''}`} />
          </button>

          {showFactors && (
            <div className="space-y-2 mb-3 animate-in slide-in-from-top-2 duration-200">
              {Object.entries(signal.factors).map(([key, factor]) => (
                <div key={key} className="flex items-center justify-between p-2 rounded-lg bg-black/20">
                  <div className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full ${factor.score > 0 ? 'bg-green-400' : factor.score < 0 ? 'bg-red-400' : 'bg-gray-400'}`}></div>
                    <span className="text-xs text-gray-400 capitalize">{key.replace(/_/g, ' ')}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-mono ${factor.score > 0 ? 'text-green-400' : factor.score < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                      {factor.score > 0 ? '+' : ''}{factor.score.toFixed(2)}
                    </span>
                    <span className="text-[10px] text-gray-600 bg-white/5 px-1.5 py-0.5 rounded">
                      {(factor.weight * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Footer Info */}
          <div className="mt-auto pt-3 border-t border-white/5">
            <div className="flex items-center justify-between text-[10px] text-gray-500">
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>{lastUpdate?.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}</span>
              </div>
              <div className="flex items-center gap-1">
                <Zap className="w-3 h-3 text-amber-500" />
                <span>{strategyInfo[selectedStrategy].description}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SPK Compliance Disclaimer */}
      <div className="mt-3 p-3 rounded-lg bg-amber-500/5 border border-amber-500/30">
        <p className="text-[9px] text-amber-400/80 text-center leading-relaxed">
          <strong>SPK Uyarısı:</strong> Bu model çıktısı yatırım tavsiyesi değildir.
          Sunulan göstergeler istatistiksel analiz sonuçlarıdır, kesinlik taşımaz.
          Yatırım kararlarınızı almadan önce lisanslı danışmana başvurunuz.
        </p>
      </div>
    </div>
  );
};

export default FusionSignals;

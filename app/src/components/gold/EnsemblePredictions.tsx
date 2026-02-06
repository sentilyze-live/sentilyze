import React, { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Activity, RefreshCw } from 'lucide-react';
import { useGoldStore, useScenarios } from '../../stores/goldStore';
import type { ScenarioModel } from '../../lib/api/gold';

type Timeframe = '1h' | '2h' | '3h';

const EnsemblePredictions: React.FC = () => {
  const scenarios = useScenarios();
  const fetchScenarios = useGoldStore((s) => s.fetchScenarios);
  const isLoadingScenarios = useGoldStore((s) => s.isLoadingScenarios);
  const errorScenarios = useGoldStore((s) => s.errorScenarios);
  const [selectedTimeframe, setSelectedTimeframe] = useState<Timeframe>('1h');

  useEffect(() => {
    fetchScenarios();
  }, [fetchScenarios]);

  if (isLoadingScenarios) {
    return (
      <div className="terminal-card p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-[var(--bg-tertiary)] rounded w-1/2 mb-4"></div>
          <div className="space-y-3">
            <div className="h-20 bg-[var(--bg-tertiary)] rounded"></div>
            <div className="h-20 bg-[var(--bg-tertiary)] rounded"></div>
            <div className="h-20 bg-[var(--bg-tertiary)] rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (errorScenarios) {
    return (
      <div className="terminal-card p-6 border-red-500/30">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-[var(--text-primary)]">Çoklu Model Senaryoları</h3>
          <button onClick={() => fetchScenarios()} className="p-2 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--bg-hover)] transition-colors">
            <RefreshCw className="w-4 h-4 text-[var(--text-muted)]" />
          </button>
        </div>
        <p className="text-red-400 text-sm">{errorScenarios}</p>
      </div>
    );
  }

  if (!scenarios) {
    return (
      <div className="terminal-card p-6">
        <h3 className="text-lg font-bold text-[var(--text-primary)] mb-2">Çoklu Model Senaryoları</h3>
        <p className="text-[var(--text-muted)] text-sm">Veri yükleniyor...</p>
      </div>
    );
  }

  const timeframes: Timeframe[] = ['1h', '2h', '3h'];
  const currentModels = scenarios.scenarios[selectedTimeframe] || [];
  const hasMultipleTimeframes = timeframes.some(tf => (scenarios.scenarios[tf]?.length || 0) > 0);

  const renderModelCard = (model: ScenarioModel) => {
    const modelName = model.model || 'Unknown';

    const getModelColor = (name: string) => {
      if (name.includes('LSTM')) return 'from-blue-500 to-cyan-500';
      if (name.includes('ARIMA')) return 'from-purple-500 to-pink-500';
      if (name.includes('XGBoost')) return 'from-green-500 to-emerald-500';
      return 'from-gray-500 to-slate-500';
    };

    const getModelIcon = (name: string) => {
      if (name.includes('LSTM')) return '🧠';
      if (name.includes('ARIMA')) return '📈';
      if (name.includes('XGBoost')) return '🌳';
      return '🤖';
    };

    return (
      <div
        key={modelName}
        className="bg-[var(--bg-tertiary)]/60 rounded-xl p-4 border border-[var(--border-color)] hover:border-[var(--gold-primary)]/30 transition-all"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{getModelIcon(modelName)}</span>
            <div>
              <p className="text-[var(--text-primary)] font-semibold text-sm">{modelName}</p>
              <p className="text-xs text-[var(--text-muted)]">Ağırlık: {((model.weight || 0) * 100).toFixed(1)}%</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-[var(--text-primary)] font-bold text-lg">₺{(model.prediction || 0).toFixed(2)}</p>
            <p className="text-xs text-[var(--text-muted)]">{((model.confidence || 0) * 100).toFixed(0)}% güven</p>
          </div>
        </div>

        {/* Weight Progress Bar */}
        <div className="w-full bg-[var(--bg-hover)] rounded-full h-2 overflow-hidden">
          <div
            className={`h-full bg-gradient-to-r ${getModelColor(modelName)} transition-all duration-500`}
            style={{ width: `${(model.weight || 0) * 100}%` }}
          />
        </div>
      </div>
    );
  };

  return (
    <div className="terminal-card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-[var(--text-primary)]">Çoklu Model Senaryoları</h3>
            <p className="text-xs text-[var(--text-muted)]">{scenarios.symbol || 'XAUUSD'} - Çoklu Model</p>
          </div>
        </div>
        <button onClick={() => fetchScenarios()} className="p-2 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--bg-hover)] transition-colors">
          <RefreshCw className={`w-4 h-4 text-[var(--text-muted)] ${isLoadingScenarios ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Ensemble Prediction */}
      <div className="bg-gradient-to-br from-[var(--gold-primary)]/20 to-[var(--gold-light)]/10 rounded-xl p-4 mb-6 border border-[var(--gold-primary)]/30">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-[var(--text-secondary)] mb-1">Birleşik Model Çıktısı</p>
            <p className="text-3xl font-bold text-[var(--gold-primary)]">
              ₺{(scenarios.ensemble_prediction || 0).toFixed(2)}
            </p>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Güven: {((scenarios.ensemble_confidence || 0) * 100).toFixed(0)}%
            </p>
          </div>
          <div className="text-right">
            {scenarios.ensemble_prediction > 0 ? (
              <TrendingUp className="w-12 h-12 text-green-400" />
            ) : (
              <TrendingDown className="w-12 h-12 text-red-400" />
            )}
          </div>
        </div>
      </div>

      {/* Timeframe Tabs - only show if data exists for multiple timeframes */}
      {hasMultipleTimeframes && (
        <div className="flex gap-2 mb-4">
          {timeframes.map((tf) => {
            const modelCount = scenarios.scenarios[tf]?.length || 0;
            return (
              <button
                key={tf}
                onClick={() => setSelectedTimeframe(tf)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  tf === selectedTimeframe
                    ? 'bg-[var(--gold-primary)] text-black'
                    : 'bg-[var(--bg-tertiary)] text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]'
                }`}
                disabled={modelCount === 0}
              >
                {tf}
                {modelCount > 0 && (
                  <span className="ml-1.5 text-[10px] opacity-70">({modelCount})</span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Model Predictions */}
      <div className="space-y-3">
        {currentModels.length > 0 ? (
          currentModels.map(renderModelCard)
        ) : (
          <p className="text-sm text-[var(--text-muted)] text-center py-4">
            Bu zaman dilimi için model verisi bulunmuyor.
          </p>
        )}
      </div>

      {/* Footer Info */}
      <div className="mt-4 pt-4 border-t border-[var(--border-color)]/30">
        <p className="text-xs text-[var(--text-muted)] text-center mb-2">
          Son Güncelleme: {new Date(scenarios.timestamp).toLocaleString('tr-TR')}
        </p>
        <p className="text-[10px] text-amber-400/60 text-center leading-relaxed">
          Bu senaryolar istatistiksel model çıktılarıdır, yatırım tavsiyesi niteliği taşımaz.
        </p>
      </div>
    </div>
  );
};

export default EnsemblePredictions;

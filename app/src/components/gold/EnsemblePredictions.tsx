import React, { useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { useGoldStore, useScenarios } from '../../stores/goldStore';
import type { ScenarioModel } from '../../lib/api/gold';

const EnsemblePredictions: React.FC = () => {
  const scenarios = useScenarios();
  const { fetchScenarios, isLoadingScenarios, errorScenarios } = useGoldStore();

  useEffect(() => {
    fetchScenarios();
  }, []);

  if (isLoadingScenarios) {
    return (
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-white/40 rounded-2xl p-6 shadow-2xl">
        <div className="animate-pulse">
          <div className="h-6 bg-white/10 rounded w-1/2 mb-4"></div>
          <div className="space-y-3">
            <div className="h-20 bg-white/10 rounded"></div>
            <div className="h-20 bg-white/10 rounded"></div>
            <div className="h-20 bg-white/10 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (errorScenarios) {
    return (
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-red-500/40 rounded-2xl p-6 shadow-2xl">
        <h3 className="text-lg font-bold text-white mb-2">AI Ensemble Tahminleri</h3>
        <p className="text-red-400 text-sm">{errorScenarios}</p>
      </div>
    );
  }

  if (!scenarios) {
    return (
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-white/40 rounded-2xl p-6 shadow-2xl">
        <h3 className="text-lg font-bold text-white mb-2">AI Ensemble Tahminleri</h3>
        <p className="text-gray-400 text-sm">Veri yükleniyor...</p>
      </div>
    );
  }

  const timeframes = ['1h', '2h', '3h'] as const;
  const currentTimeframe = '1h';

  const renderModelCard = (model: ScenarioModel) => {
    const getModelColor = (modelName: string) => {
      if (modelName.includes('LSTM')) return 'from-blue-500 to-cyan-500';
      if (modelName.includes('ARIMA')) return 'from-purple-500 to-pink-500';
      if (modelName.includes('XGBoost')) return 'from-green-500 to-emerald-500';
      return 'from-gray-500 to-slate-500';
    };

    const getModelIcon = (modelName: string) => {
      if (modelName.includes('LSTM')) return '🧠';
      if (modelName.includes('ARIMA')) return '📈';
      if (modelName.includes('XGBoost')) return '🌳';
      return '🤖';
    };

    return (
      <div
        key={model.model}
        className="bg-[var(--bg-tertiary)]/60 rounded-xl p-4 border border-white/20 hover:border-white/40 transition-all"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{getModelIcon(model.model)}</span>
            <div>
              <p className="text-white font-semibold text-sm">{model.model}</p>
              <p className="text-xs text-gray-400">Ağırlık: {(model.weight * 100).toFixed(1)}%</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-white font-bold text-lg">₺{model.prediction.toFixed(2)}</p>
            <p className="text-xs text-gray-400">{(model.confidence * 100).toFixed(0)}% güven</p>
          </div>
        </div>

        {/* Weight Progress Bar */}
        <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
          <div
            className={`h-full bg-gradient-to-r ${getModelColor(model.model)} transition-all duration-500`}
            style={{ width: `${model.weight * 100}%` }}
          />
        </div>
      </div>
    );
  };

  return (
    <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-white/40 rounded-2xl p-6 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">AI Ensemble Tahminleri</h3>
            <p className="text-xs text-gray-400">{scenarios.symbol} - Çoklu Model</p>
          </div>
        </div>
      </div>

      {/* Ensemble Prediction */}
      <div className="bg-gradient-to-br from-[var(--gold-primary)]/20 to-[var(--gold-light)]/10 rounded-xl p-4 mb-6 border border-[var(--gold-primary)]/30">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-300 mb-1">Ensemble Tahmini</p>
            <p className="text-3xl font-bold text-[var(--gold-primary)]">
              ₺{scenarios.ensemble_prediction.toFixed(2)}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Güven: {(scenarios.ensemble_confidence * 100).toFixed(0)}%
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

      {/* Timeframe Tabs */}
      <div className="flex gap-2 mb-4">
        {timeframes.map((tf) => (
          <button
            key={tf}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tf === currentTimeframe
                ? 'bg-[var(--gold-primary)] text-black'
                : 'bg-white/10 text-gray-300 hover:bg-white/20'
            }`}
          >
            {tf}
          </button>
        ))}
      </div>

      {/* Model Predictions */}
      <div className="space-y-3">
        {scenarios.scenarios[currentTimeframe]?.map(renderModelCard)}
      </div>

      {/* Footer Info */}
      <div className="mt-4 pt-4 border-t border-white/10">
        <p className="text-xs text-gray-400 text-center">
          Son Güncelleme: {new Date(scenarios.timestamp).toLocaleString('tr-TR')}
        </p>
      </div>
    </div>
  );
};

export default EnsemblePredictions;

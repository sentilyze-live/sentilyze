import React, { useEffect } from 'react';
import { Award, CheckCircle2, Target, TrendingUp } from 'lucide-react';
import { useGoldStore, useDailyReport } from '../../stores/goldStore';

const PerformanceMetrics: React.FC = () => {
  const dailyReport = useDailyReport();
  const { fetchDailyReport, isLoadingDailyReport, errorDailyReport } = useGoldStore();

  useEffect(() => {
    fetchDailyReport();
  }, []);

  if (isLoadingDailyReport) {
    return (
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-white/40 rounded-2xl p-6 shadow-2xl">
        <div className="animate-pulse">
          <div className="h-6 bg-white/10 rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-3 gap-4">
            <div className="h-24 bg-white/10 rounded"></div>
            <div className="h-24 bg-white/10 rounded"></div>
            <div className="h-24 bg-white/10 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (errorDailyReport) {
    return (
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-red-500/40 rounded-2xl p-6 shadow-2xl">
        <h3 className="text-lg font-bold text-white mb-2">Performans Metrikleri</h3>
        <p className="text-red-400 text-sm">{errorDailyReport}</p>
      </div>
    );
  }

  if (!dailyReport) {
    return (
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-white/40 rounded-2xl p-6 shadow-2xl">
        <h3 className="text-lg font-bold text-white mb-2">Performans Metrikleri</h3>
        <p className="text-gray-400 text-sm">Veri yükleniyor...</p>
      </div>
    );
  }

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 0.7) return 'from-green-600 to-emerald-500';
    if (accuracy >= 0.5) return 'from-yellow-600 to-yellow-500';
    return 'from-red-600 to-red-500';
  };

  const getAccuracyBadgeColor = (accuracy: number) => {
    if (accuracy >= 0.7) return 'bg-green-500/20 text-green-400 border-green-500/30';
    if (accuracy >= 0.5) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    return 'bg-red-500/20 text-red-400 border-red-500/30';
  };

  const getModelIcon = (modelName: string) => {
    if (modelName.includes('LSTM')) return '🧠';
    if (modelName.includes('ARIMA')) return '📈';
    if (modelName.includes('XGBoost')) return '🌳';
    if (modelName.includes('Ensemble')) return '🎯';
    return '🤖';
  };

  return (
    <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-lg border border-white/40 rounded-2xl p-6 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
            <Award className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Günlük Performans Raporu</h3>
            <p className="text-xs text-gray-400">{dailyReport.date}</p>
          </div>
        </div>
      </div>

      {/* Overall Metrics */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-gradient-to-br from-[var(--gold-primary)]/20 to-[var(--gold-light)]/10 rounded-xl p-4 border border-[var(--gold-primary)]/30">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-5 h-5 text-[var(--gold-primary)]" />
            <p className="text-sm text-gray-300">Genel Doğruluk</p>
          </div>
          <p className="text-3xl font-bold text-[var(--gold-primary)]">
            {(dailyReport.overall_accuracy * 100).toFixed(1)}%
          </p>
          <div className="mt-2 w-full bg-white/10 rounded-full h-2">
            <div
              className={`h-full bg-gradient-to-r ${getAccuracyColor(dailyReport.overall_accuracy)} rounded-full`}
              style={{ width: `${dailyReport.overall_accuracy * 100}%` }}
            />
          </div>
        </div>

        <div className="bg-[var(--bg-tertiary)]/60 rounded-xl p-4 border border-white/20">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-5 h-5 text-blue-400" />
            <p className="text-sm text-gray-300">Toplam Tahmin</p>
          </div>
          <p className="text-3xl font-bold text-white">{dailyReport.total_predictions}</p>
          <p className="text-xs text-gray-400 mt-1">İşlenen tahmin sayısı</p>
        </div>

        <div className="bg-[var(--bg-tertiary)]/60 rounded-xl p-4 border border-white/20">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-5 h-5 text-green-400" />
            <p className="text-sm text-gray-300">Doğru Tahmin</p>
          </div>
          <p className="text-3xl font-bold text-green-400">{dailyReport.correct_predictions}</p>
          <p className="text-xs text-gray-400 mt-1">Başarılı tahmin sayısı</p>
        </div>
      </div>

      {/* Trust Badges */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className={`rounded-lg px-3 py-2 border ${getAccuracyBadgeColor(dailyReport.overall_accuracy)} text-center`}>
          <p className="text-lg font-bold">
            {dailyReport.overall_accuracy >= 0.7 ? 'Yüksek' : dailyReport.overall_accuracy >= 0.5 ? 'Orta' : 'Düşük'}
          </p>
          <p className="text-xs opacity-80">Güvenilirlik</p>
        </div>
        <div className="rounded-lg px-3 py-2 border bg-blue-500/20 text-blue-400 border-blue-500/30 text-center">
          <p className="text-lg font-bold">AI</p>
          <p className="text-xs opacity-80">Destekli</p>
        </div>
        <div className="rounded-lg px-3 py-2 border bg-purple-500/20 text-purple-400 border-purple-500/30 text-center">
          <p className="text-lg font-bold">24/7</p>
          <p className="text-xs opacity-80">Aktif</p>
        </div>
      </div>

      {/* Model Performance Breakdown */}
      <div>
        <p className="text-sm text-gray-300 font-semibold mb-4">Model Bazında Performans</p>
        <div className="space-y-3">
          {dailyReport.models.map((model, idx) => (
            <div
              key={idx}
              className="bg-[var(--bg-tertiary)]/40 rounded-xl p-4 border border-white/20 hover:border-white/30 transition-all"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{getModelIcon(model.model_name)}</span>
                  <div>
                    <p className="text-white font-semibold text-sm">{model.model_name}</p>
                    <p className="text-xs text-gray-400">{model.predictions_count} tahmin</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xl font-bold text-white">{(model.accuracy * 100).toFixed(1)}%</p>
                  <p className={`text-xs ${model.accuracy >= 0.7 ? 'text-green-400' : model.accuracy >= 0.5 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {model.accuracy >= 0.7 ? 'Mükemmel' : model.accuracy >= 0.5 ? 'İyi' : 'Gelişiyor'}
                  </p>
                </div>
              </div>

              {/* Model Accuracy Bar */}
              <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full bg-gradient-to-r ${getAccuracyColor(model.accuracy)} transition-all duration-500`}
                  style={{ width: `${model.accuracy * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Info */}
      <div className="mt-6 pt-4 border-t border-white/10">
        <p className="text-xs text-gray-400 text-center">
          Günlük performans verileri her gün otomatik güncellenir. Tüm tahminler geçmiş verilerle karşılaştırılır.
        </p>
      </div>
    </div>
  );
};

export default PerformanceMetrics;

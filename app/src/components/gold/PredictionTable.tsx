import React, { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus, AlertTriangle, BarChart3, Clock, Target } from 'lucide-react';
import { getPredictionScenarios, getDailyAnalysisReport, type PredictionScenario, type DailyAnalysisReport } from '../../lib/api/realApi';

const PredictionTable: React.FC = () => {
  const [scenarios, setScenarios] = useState<PredictionScenario[]>([]);
  const [dailyReport, setDailyReport] = useState<DailyAnalysisReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'scenarios' | 'performance'>('scenarios');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const [scenariosData, reportData] = await Promise.all([
          getPredictionScenarios(),
          getDailyAnalysisReport()
        ]);

        if (scenariosData && scenariosData.length > 0) {
          // Filter to only show desired timeframes: 30dk, 1 saat, 3 saat, 6 saat
          const desiredTimeframes = ['30 Dakika', '1 Saat', '3 Saat', '6 Saat'];
          const filteredScenarios = scenariosData.filter(s =>
            desiredTimeframes.some(tf => s.timeframe.includes(tf))
          );
          setScenarios(filteredScenarios.length > 0 ? filteredScenarios : scenariosData);
        }
        if (reportData) {
          setDailyReport(reportData);
        }
      } catch (err) {
        console.error('Failed to fetch prediction data:', err);
        setError('Senaryo verileri alınamadı');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 120000); // Her 2 dakikada bir güncelle (optimize edildi)
    return () => clearInterval(interval);
  }, []);

  const getScoreColor = (score: number): string => {
    if (score >= 75) return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
    if (score >= 60) return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
    return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
  };

  const getDirectionColor = (direction: string): string => {
    switch (direction.toLowerCase()) {
      case 'up':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      case 'down':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
      default:
        return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
    }
  };

  const getDirectionIcon = (direction: string) => {
    switch (direction.toLowerCase()) {
      case 'up':
        return <TrendingUp className="w-4 h-4" />;
      case 'down':
        return <TrendingDown className="w-4 h-4" />;
      default:
        return <Minus className="w-4 h-4" />;
    }
  };

  const getDirectionLabel = (direction: string): string => {
    switch (direction.toLowerCase()) {
      case 'up': return 'YUKARI';
      case 'down': return 'AŞAĞI';
      default: return 'YATAY';
    }
  };

  const avgScore = scenarios.length > 0
    ? Math.round(scenarios.reduce((sum, p) => sum + p.confidenceScore, 0) / scenarios.length)
    : 0;

  return (
    <div className="glass-card p-6 mb-6">
      {/* Legal Disclaimer - Önemli */}
      <div className="mb-6 p-4 bg-rose-500/5 border border-rose-500/30 rounded-lg">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-rose-200 font-semibold mb-1">
              Yasal Uyarı - Yatırım Tavsiyesi Değildir
            </p>
            <p className="text-xs text-rose-200/80 leading-relaxed">
              Aşağıda sunulan veriler yapay zeka modelleri (LSTM, ARIMA, XGBoost) tarafından 
              oluşturulan <strong>hipotetik senaryo analizleridir</strong> ve gerçek piyasa 
              koşullarından farklılık gösterebilir. Bu analizler <strong>kesinlikle yatırım 
              tavsiyesi niteliği taşımaz</strong>. Sentilyze, 6362 sayılı Sermaye Piyasası 
              Kanunu kapsamında portföy yönetimi veya yatırım danışmanlığı faaliyetinde 
              bulunmamaktadır. Finansal kararlarınızı vermeden önce SPK lisanslı bir aracı 
              kurum ve/veya portföy yöneticisine danışmanız önemle tavsiye edilir.
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-blue-400 flex items-center gap-2">
            <BarChart3 className="w-6 h-6" />
            FİYAT TAHMİN SENARYOLARl
          </h2>
          <p className="text-xs text-[#5F6B7A] mt-1">
            30 dakika, 1 saat, 3 saat ve 6 saat sonraki fiyat tahminleri (LSTM + ARIMA + XGBoost modelleri)
          </p>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('scenarios')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'scenarios'
                ? 'bg-blue-500 text-white'
                : 'bg-[#1A2230] text-[#9AA4B2] hover:text-white'
            }`}
          >
            Senaryolar
          </button>
          <button
            onClick={() => setActiveTab('performance')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'performance'
                ? 'bg-blue-500 text-white'
                : 'bg-[#1A2230] text-[#9AA4B2] hover:text-white'
            }`}
          >
            <Target className="w-4 h-4 inline mr-1" />
            Başarı Raporu
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-8">
          <span className="text-[#9AA4B2]">Senaryolar yükleniyor...</span>
        </div>
      ) : error ? (
        <div className="text-center py-8 text-rose-400">{error}</div>
      ) : activeTab === 'scenarios' ? (
        <>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#1F2A38]">
                  <th className="text-left py-3 px-3 text-[#9AA4B2] font-semibold text-sm">
                    <Clock className="w-4 h-4 inline mr-1" />
                    Zaman
                  </th>
                  <th className="text-center py-3 px-3 text-[#9AA4B2] font-semibold text-sm">
                    Senaryo Fiyatı (TRY/Gram)
                  </th>
                  <th className="text-center py-3 px-3 text-[#9AA4B2] font-semibold text-sm">
                    Güven Skoru
                  </th>
                  <th className="text-center py-3 px-3 text-[#9AA4B2] font-semibold text-sm">
                    Yön
                  </th>
                  <th className="text-center py-3 px-3 text-[#9AA4B2] font-semibold text-sm">
                    Modeller
                  </th>
                </tr>
              </thead>
              <tbody>
                {scenarios.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-[#9AA4B2]">
                      Senaryo verisi bulunamadı
                    </td>
                  </tr>
                ) : (
                  scenarios.map((item, index) => {
                    const isPositive = item.changePercent >= 0;
                    return (
                      <tr 
                        key={item.timeframe}
                        className={`border-b border-[#1F2A38]/50 hover:bg-[#1A2230]/50 transition-colors ${
                          index === scenarios.length - 1 ? 'border-b-0' : ''
                        }`}
                      >
                        <td className="py-4 px-3 text-[#E6EDF3] font-medium">
                          {item.timeframe}
                        </td>
                        <td className="py-4 px-3 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <span className="font-mono text-[#E6EDF3] font-semibold">
                              {item.price.toFixed(2)} TL
                            </span>
                            <span className={`text-sm ${isPositive ? 'text-blue-400' : 'text-rose-400'}`}>
                              {isPositive ? '+' : ''}{item.changePercent.toFixed(2)}%
                            </span>
                          </div>
                        </td>
                        <td className="py-4 px-3 text-center">
                          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold border ${getScoreColor(item.confidenceScore)}`}>
                            %{item.confidenceScore}
                          </span>
                        </td>
                        <td className="py-4 px-3 text-center">
                          <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-semibold border ${getDirectionColor(item.direction)}`}>
                            {getDirectionIcon(item.direction)}
                            {getDirectionLabel(item.direction)}
                          </span>
                        </td>
                        <td className="py-4 px-3 text-center">
                          <div className="flex flex-wrap justify-center gap-1">
                            {item.models?.map((model) => (
                              <span
                                key={model.name}
                                className="text-xs px-2 py-0.5 bg-[#1A2230] text-[#9AA4B2] rounded"
                                title={`Ağırlık: %${(model.weight * 100).toFixed(0)}`}
                              >
                                {model.name}
                              </span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-4 pt-4 border-t border-[#1F2A38] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div className="text-sm text-[#9AA4B2]">
              <span className="text-[#5F6B7A]">Kullanılan Modeller:</span>{' '}
              <span className="text-[#E6EDF3]">LSTM + ARIMA + XGBoost Ensemble</span>
            </div>
            {scenarios.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-[#9AA4B2]">Ortalama Güven:</span>
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold border ${getScoreColor(avgScore)}`}>
                  %{avgScore}
                </span>
              </div>
            )}
          </div>
        </>
      ) : (
        /* Performance Report Tab */
        <div className="space-y-6">
          {dailyReport ? (
            <>
              {/* Overall Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-[#1A2230]/50 rounded-lg p-4 text-center">
                  <p className="text-sm text-[#9AA4B2] mb-1">Genel Başarı Oranı</p>
                  <p className="text-3xl font-bold text-blue-400">%{dailyReport.accuracy.toFixed(1)}</p>
                </div>
                <div className="bg-[#1A2230]/50 rounded-lg p-4 text-center">
                  <p className="text-sm text-[#9AA4B2] mb-1">Toplam Senaryo</p>
                  <p className="text-3xl font-bold text-[#E6EDF3]">{dailyReport.totalPredictions}</p>
                </div>
                <div className="bg-[#1A2230]/50 rounded-lg p-4 text-center">
                  <p className="text-sm text-[#9AA4B2] mb-1">Doğru Senaryolar</p>
                  <p className="text-3xl font-bold text-emerald-400">{dailyReport.correctPredictions}</p>
                </div>
              </div>

              {/* Scenario Performance */}
              <div>
                <h3 className="text-sm font-semibold text-[#9AA4B2] mb-3">Zaman Bazlı Performans</h3>
                <div className="space-y-2">
                  {dailyReport.scenarios?.map((scenario) => (
                    <div
                      key={scenario.timeframe}
                      className="flex items-center justify-between p-3 bg-[#1A2230]/30 rounded-lg"
                    >
                      <span className="text-[#E6EDF3]">{scenario.timeframe}</span>
                      <div className="flex items-center gap-4">
                        <span className="text-sm text-[#9AA4B2]">
                          Tahmin: {scenario.predicted.toFixed(2)} / Gerçek: {scenario.actual.toFixed(2)}
                        </span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          scenario.status === 'success' ? 'bg-emerald-500/20 text-emerald-400' :
                          scenario.status === 'partial' ? 'bg-amber-500/20 text-amber-400' :
                          'bg-rose-500/20 text-rose-400'
                        }`}>
                          %{scenario.accuracy.toFixed(0)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Model Performance */}
              <div>
                <h3 className="text-sm font-semibold text-[#9AA4B2] mb-3">Model Performansı</h3>
                <div className="space-y-3">
                  {dailyReport.modelPerformance?.map((model) => (
                    <div key={model.model} className="flex items-center gap-3">
                      <span className="text-[#E6EDF3] w-20">{model.model}</span>
                      <div className="flex-1 h-2 bg-[#1A2230] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full transition-all duration-500"
                          style={{ width: `${model.accuracy}%` }}
                        />
                      </div>
                      <span className="text-sm text-[#9AA4B2] w-16 text-right">
                        %{model.accuracy.toFixed(0)}
                      </span>
                      <span className="text-xs text-[#5F6B7A]">
                        Ağırlık: %{(model.weight * 100).toFixed(0)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="text-center py-8 text-[#9AA4B2]">
              Günlük rapor verisi bulunamadı
            </div>
          )}
        </div>
      )}

      {/* Additional Disclaimer */}
      <div className="mt-6 p-3 bg-[#1F2A38]/50 rounded-lg border border-[#1F2A38]">
        <p className="text-xs text-[#9AA4B2] leading-relaxed">
          <strong className="text-rose-400">Önemli Not:</strong> Geçmiş performans gelecekteki 
          sonuçların göstergesi değildir. Yapay zeka modelleri piyasa koşullarındaki ani değişikliklere 
          ve beklenmedik olaylara (siyah kuğu olayları) karşı duyarlıdır. Bu platformda sunulan tüm 
          veriler eğitim ve araştırma amaçlıdır. Yatırım yapmadan önce risk profilinizi dikkatle 
          değerlendiriniz.
        </p>
      </div>
    </div>
  );
};

export default PredictionTable;
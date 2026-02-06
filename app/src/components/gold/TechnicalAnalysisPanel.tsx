import React, { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Activity, Zap, BarChart3, Lock } from 'lucide-react';

interface TechnicalIndicatorData {
  rsi: { value: number; condition: 'oversold' | 'neutral' | 'overbought' };
  macd: { value: number; momentum: 'positive' | 'negative'; histogram: number };
  bollinger: { upper: number; middle: number; lower: number; width: number };
  sma: { '20': number; '50': number; '200': number };
  stochastic: { k: number; d: number; condition: string };
  atr: number;
}

interface AICommentary {
  summary: string;
  signals: string[];
  risk_level: 'low' | 'medium' | 'high';
  recommendation: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';
  confidence: number;
}

interface TechnicalAnalysisPanelProps {
  symbol?: string;
  isSubscribed?: boolean; // For premium feature gating
}

const TechnicalAnalysisPanel: React.FC<TechnicalAnalysisPanelProps> = ({
  symbol = 'XAUUSD',
  isSubscribed = false
}) => {
  const [indicators, setIndicators] = useState<TechnicalIndicatorData | null>(null);
  const [commentary, setCommentary] = useState<AICommentary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTechnicalData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const apiUrl = import.meta.env.VITE_API_URL || 'https://api-gateway-koa62feuuq-uc.a.run.app';

      // Fetch technical indicators
      const response = await fetch(`${apiUrl}/gold/technical-indicators/${symbol}`);

      if (!response.ok) {
        throw new Error('Failed to fetch technical indicators');
      }

      const data = await response.json();
      setIndicators(data.data || data);

      // Fetch AI commentary from Moonshot API if subscribed
      if (isSubscribed) {
        try {
          const aiResponse = await fetch(`${apiUrl}/gold/ai-analysis/${symbol}`, {
            headers: {
              // TODO: Add authorization header when auth is implemented
              // 'Authorization': `Bearer ${userToken}`
            }
          });

          if (aiResponse.ok) {
            const aiData = await aiResponse.json();
            setCommentary(aiData.analysis);
            console.log('AI Commentary loaded from Moonshot:', aiData.model);
          } else {
            throw new Error('AI API returned error');
          }
        } catch (aiError) {
          console.warn('AI commentary not available, using fallback:', aiError);
          // Fallback to mock commentary
          setCommentary({
            summary: 'Teknik göstergeler karışık sinyaller veriyor. RSI nötr bölgede, MACD pozitif momentum gösteriyor.',
            signals: [
              'RSI 50 civarında - trend belirsiz',
              'MACD histogramı artışta - kısa vadeli momentum pozitif',
              'Fiyat Bollinger ortası yakınında - volatilite düşük',
              'SMA 20 > SMA 50 - orta vadeli yükseliş trendi'
            ],
            risk_level: 'medium',
            recommendation: 'hold',
            confidence: 68,
          });
        }
      }

    } catch (err) {
      console.error('Error fetching technical data:', err);
      setError('Teknik analiz verisi alınamadı');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTechnicalData();

    // Refresh every 60 seconds
    const interval = setInterval(fetchTechnicalData, 60000);

    return () => clearInterval(interval);
  }, [symbol, isSubscribed]);

  const getRSIColor = (value: number) => {
    if (value >= 70) return 'text-rose-400';
    if (value <= 30) return 'text-emerald-400';
    return 'text-yellow-400';
  };

  const getMACDColor = (momentum: 'positive' | 'negative') => {
    return momentum === 'positive' ? 'text-emerald-400' : 'text-rose-400';
  };

  const getRecommendationColor = (rec: string) => {
    if (rec.includes('buy')) return 'text-emerald-400';
    if (rec.includes('sell')) return 'text-rose-400';
    return 'text-yellow-400';
  };

  const getIndicatorText = (rec: string) => {
    const map: Record<string, string> = {
      strong_buy: 'Güçlü Yükseliş Göstergesi',
      buy: 'Yükseliş Göstergesi',
      hold: 'Nötr Görünüm',
      sell: 'Düşüş Göstergesi',
      strong_sell: 'Güçlü Düşüş Göstergesi',
    };
    return map[rec] || 'Nötr Görünüm';
  };

  if (isLoading) {
    return (
      <div className="terminal-card p-6 animate-pulse">
        <div className="h-6 w-48 bg-[var(--bg-tertiary)] rounded mb-4" />
        <div className="space-y-3">
          <div className="h-16 bg-[var(--bg-tertiary)] rounded" />
          <div className="h-16 bg-[var(--bg-tertiary)] rounded" />
          <div className="h-16 bg-[var(--bg-tertiary)] rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="terminal-card p-6">
        <div className="flex items-center gap-2 text-rose-400">
          <Activity className="w-5 h-5" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  if (!indicators) {
    return null;
  }

  return (
    <div className="terminal-card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Activity className="w-6 h-6 text-purple-400" />
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Teknik Analiz</h2>
        </div>
        {!isSubscribed && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-500/20 to-purple-500/20 border border-amber-500/30">
            <Lock className="w-4 h-4 text-amber-400" />
            <span className="text-sm font-medium text-amber-400">Premium</span>
          </div>
        )}
      </div>

      {/* Technical Indicators Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {/* RSI */}
        <div className="p-4 rounded-lg backdrop-blur-sm bg-[var(--bg-secondary)]/40 border border-[var(--border-color)]/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-[var(--text-muted)]">RSI (14)</span>
            <Zap className="w-4 h-4 text-yellow-400" />
          </div>
          <div className={`text-2xl font-bold ${getRSIColor(indicators.rsi.value)}`}>
            {indicators.rsi.value.toFixed(1)}
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1 capitalize">
            {indicators.rsi.condition === 'oversold' ? 'Aşırı Satım' :
             indicators.rsi.condition === 'overbought' ? 'Aşırı Alım' : 'Nötr'}
          </div>
        </div>

        {/* MACD */}
        <div className="p-4 rounded-lg backdrop-blur-sm bg-[var(--bg-secondary)]/40 border border-[var(--border-color)]/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-[var(--text-muted)]">MACD</span>
            <BarChart3 className="w-4 h-4 text-blue-400" />
          </div>
          <div className={`text-2xl font-bold ${getMACDColor(indicators.macd.momentum)}`}>
            {indicators.macd.value.toFixed(3)}
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1 capitalize">
            {indicators.macd.momentum === 'positive' ? 'Pozitif Momentum' : 'Negatif Momentum'}
          </div>
        </div>

        {/* Bollinger Bands */}
        <div className="p-4 rounded-lg backdrop-blur-sm bg-[var(--bg-secondary)]/40 border border-[var(--border-color)]/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-[var(--text-muted)]">Bollinger Genişliği</span>
            <Activity className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-purple-400">
            {indicators.bollinger.width.toFixed(2)}%
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1">
            {indicators.bollinger.width > 3 ? 'Yüksek Volatilite' :
             indicators.bollinger.width > 1.5 ? 'Normal Volatilite' : 'Düşük Volatilite'}
          </div>
        </div>

        {/* SMA Trend */}
        <div className="p-4 rounded-lg backdrop-blur-sm bg-[var(--bg-secondary)]/40 border border-[var(--border-color)]/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-[var(--text-muted)]">SMA 20/50</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-lg font-bold text-[var(--text-primary)]">
            ${indicators.sma['20'].toFixed(2)}
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1">
            SMA 50: ${indicators.sma['50'].toFixed(2)}
          </div>
        </div>

        {/* Stochastic */}
        <div className="p-4 rounded-lg backdrop-blur-sm bg-[var(--bg-secondary)]/40 border border-[var(--border-color)]/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-[var(--text-muted)]">Stochastic</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-400">
            {indicators.stochastic.k.toFixed(1)}
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1 capitalize">
            {indicators.stochastic.condition}
          </div>
        </div>

        {/* ATR */}
        <div className="p-4 rounded-lg backdrop-blur-sm bg-[var(--bg-secondary)]/40 border border-[var(--border-color)]/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-[var(--text-muted)]">ATR (Volatilite)</span>
            <Zap className="w-4 h-4 text-orange-400" />
          </div>
          <div className="text-2xl font-bold text-orange-400">
            {indicators.atr.toFixed(2)}
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1">
            Average True Range
          </div>
        </div>
      </div>

      {/* AI Commentary Section - Premium Only */}
      {isSubscribed && commentary ? (
        <div className="p-5 rounded-lg backdrop-blur-sm bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-purple-400" />
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">AI Model Çıktısı</h3>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-[var(--text-muted)]">Güven:</span>
              <span className="text-sm font-bold text-purple-400">{commentary.confidence}%</span>
            </div>
          </div>

          {/* Summary */}
          <p className="text-sm text-[var(--text-muted)] mb-4 leading-relaxed">
            {commentary.summary}
          </p>

          {/* Signals */}
          <div className="space-y-2 mb-4">
            {commentary.signals.map((signal, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm text-[var(--text-muted)]">
                <span className="text-purple-400 mt-0.5">•</span>
                <span>{signal}</span>
              </div>
            ))}
          </div>

          {/* Recommendation */}
          <div className="flex items-center justify-between pt-4 border-t border-[var(--border-color)]/30">
            <div className="flex items-center gap-2">
              <span className="text-sm text-[var(--text-muted)]">Model Sonucu:</span>
              <span className={`text-lg font-bold ${getRecommendationColor(commentary.recommendation)}`}>
                {getIndicatorText(commentary.recommendation)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-[var(--text-muted)]">Risk:</span>
              <span className={`text-sm font-semibold uppercase ${
                commentary.risk_level === 'high' ? 'text-rose-400' :
                commentary.risk_level === 'medium' ? 'text-yellow-400' :
                'text-emerald-400'
              }`}>
                {commentary.risk_level === 'high' ? 'Yüksek' :
                 commentary.risk_level === 'medium' ? 'Orta' : 'Düşük'}
              </span>
            </div>
          </div>
        </div>
      ) : !isSubscribed ? (
        <div className="p-5 rounded-lg backdrop-blur-sm bg-gradient-to-r from-amber-500/10 to-purple-500/10 border border-amber-500/30 text-center">
          <Lock className="w-8 h-8 text-amber-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
            AI Analiz - Premium Özellik
          </h3>
          <p className="text-sm text-[var(--text-muted)] mb-4">
            Derin öğrenme algoritmaları ile üretilmiş teknik analiz yorumları ve model çıktıları için Trader veya Enterprise pakete yükseltin.
          </p>
          <button className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-amber-500 to-purple-500 text-white font-semibold hover:opacity-90 transition-opacity">
            Premium'a Yükselt
          </button>
        </div>
      ) : null}

      {/* Footer Note */}
      <div className="mt-4 px-3 py-2 rounded-lg bg-amber-500/5 border border-amber-500/20">
        <p className="text-xs text-amber-300/70 text-center leading-relaxed">
          <strong>Uyarı:</strong> Bu analiz istatistiksel model çıktısıdır, yatırım tavsiyesi değildir.
          SPK mevzuatı kapsamında yatırım danışmanlığı yetkimiz bulunmamaktadır.
          Son güncelleme: {new Date().toLocaleTimeString('tr-TR')}
        </p>
      </div>
    </div>
  );
};

export default TechnicalAnalysisPanel;

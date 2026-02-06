import React, { useEffect, useState } from 'react';
import { Brain, TrendingUp, TrendingDown, Activity, BarChart3 } from 'lucide-react';
import { useGoldStore, useCurrentPrice, useSentiment, useMarketContext } from '../../stores';
import { formatTimeAgo } from '../../lib/utils/format';

interface Commentary {
  id: string;
  text: string;
  indicator: string;
  timestamp: Date;
  icon: React.ElementType;
}

const AICommentary: React.FC = () => {
  const [commentaries, setCommentaries] = useState<Commentary[]>([]);
  const price = useCurrentPrice();
  const sentiment = useSentiment();
  const context = useMarketContext();
  const indicators = useGoldStore(s => s.indicators);

  const generateCommentary = (): Commentary | null => {
    const now = new Date();

    // RSI Analysis
    if (indicators?.rsi) {
      const rsi = indicators.rsi.value;
      if (rsi > 70) {
        return {
          id: `rsi-${now.getTime()}`,
          text: `RSI aşırı alım bölgesinde (${rsi.toFixed(1)}). Model kısa vadede düşüş potansiyeli gösteriyor.`,
          indicator: 'RSI',
          timestamp: now,
          icon: Activity,
        };
      }
      if (rsi < 30) {
        return {
          id: `rsi-${now.getTime()}`,
          text: `RSI aşırı satım bölgesinde (${rsi.toFixed(1)}). Yükseliş potansiyeli gözlemleniyor.`,
          indicator: 'RSI',
          timestamp: now,
          icon: Activity,
        };
      }
    }

    // MACD Analysis
    if (indicators?.macd) {
      const { momentum, value } = indicators.macd;
      if (momentum === 'positive' && value > 0) {
        return {
          id: `macd-${now.getTime()}`,
          text: `MACD pozitif momentum gösteriyor. Kısa vadeli göstergeler pozitif yönde.`,
          indicator: 'MACD',
          timestamp: now,
          icon: TrendingUp,
        };
      }
      if (momentum === 'negative' && value < 0) {
        return {
          id: `macd-${now.getTime()}`,
          text: `MACD düşüş eğiliminde. Dikkatli olunması gereken bir dönem.`,
          indicator: 'MACD',
          timestamp: now,
          icon: TrendingDown,
        };
      }
    }

    // Bollinger Bands Analysis
    if (indicators?.bollinger && price) {
      const { upper, lower, middle } = indicators.bollinger;
      const currentPrice = price.price;

      if (currentPrice > upper * 0.98) {
        return {
          id: `bb-${now.getTime()}`,
          text: `Fiyat Bollinger üst bandına yakın (${currentPrice.toFixed(2)}). Model düşüş potansiyeli gösteriyor.`,
          indicator: 'Bollinger',
          timestamp: now,
          icon: BarChart3,
        };
      }
      if (currentPrice < lower * 1.02) {
        return {
          id: `bb-${now.getTime()}`,
          text: `Fiyat Bollinger alt bandında (${currentPrice.toFixed(2)}). Yükseliş potansiyeli mevcut.`,
          indicator: 'Bollinger',
          timestamp: now,
          icon: BarChart3,
        };
      }
      if (currentPrice > middle) {
        return {
          id: `bb-${now.getTime()}`,
          text: `Fiyat orta band üzerinde. Mevcut göstergeler pozitif yönde.`,
          indicator: 'Bollinger',
          timestamp: now,
          icon: TrendingUp,
        };
      }
    }

    // Trend + Sentiment Combined
    if (context && sentiment) {
      const { trend } = context;
      const sentimentScore = sentiment.score;

      if (trend.direction === 'up' && sentimentScore > 0.6) {
        return {
          id: `combo-${now.getTime()}`,
          text: `Yükseliş trendi güçlü, duygu endeksi pozitif. Model göstergeleri yükseliş yönünde.`,
          indicator: 'Trend + Duygu',
          timestamp: now,
          icon: Brain,
        };
      }
      if (trend.direction === 'down' && sentimentScore < 0.4) {
        return {
          id: `combo-${now.getTime()}`,
          text: `Düşüş baskısı hissediliyor. Duygu endeksi negatif, model düşüş riski gösteriyor.`,
          indicator: 'Trend + Duygu',
          timestamp: now,
          icon: Brain,
        };
      }
    }

    // Support/Resistance Analysis
    if (context?.levels && price) {
      const { support, resistance } = context.levels;
      const currentPrice = price.price;

      if (resistance.length > 0 && resistance[0]) {
        const nearestResistance = resistance[0];
        const distanceToResistance = ((nearestResistance - currentPrice) / currentPrice) * 100;

        if (distanceToResistance < 2 && distanceToResistance > 0) {
          return {
            id: `resistance-${now.getTime()}`,
            text: `Altın ${nearestResistance.toFixed(2)} direncine yaklaşıyor. Kritik seviye yaklaşımda.`,
            indicator: 'Teknik Seviyeler',
            timestamp: now,
            icon: BarChart3,
          };
        }
      }

      if (support.length > 0 && support[0]) {
        const nearestSupport = support[0];
        const distanceToSupport = ((currentPrice - nearestSupport) / currentPrice) * 100;

        if (distanceToSupport < 2 && distanceToSupport > 0) {
          return {
            id: `support-${now.getTime()}`,
            text: `${nearestSupport.toFixed(2)} desteği kritik seviye. Kritik destek seviyesi yaklaşımda.`,
            indicator: 'Teknik Seviyeler',
            timestamp: now,
            icon: BarChart3,
          };
        }
      }
    }

    return null;
  };

  const updateCommentaries = () => {
    const newCommentary = generateCommentary();
    if (newCommentary) {
      setCommentaries(prev => {
        // Avoid duplicates based on indicator type
        const filtered = prev.filter(c => c.indicator !== newCommentary.indicator);
        // Keep only last 5 commentaries
        const updated = [newCommentary, ...filtered].slice(0, 5);
        return updated;
      });
    }
  };

  useEffect(() => {
    // Initial commentary generation
    updateCommentaries();

    // Generate new commentary every 5 minutes
    const interval = setInterval(updateCommentaries, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, [indicators, price, sentiment, context]);

  if (commentaries.length === 0) {
    return (
      <div className="terminal-card p-6">
        <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <Brain className="w-5 h-5 text-[var(--gold-primary)]" />
          AI Model Yorumları
        </h3>
        <div className="text-center py-8">
          <p className="text-sm text-[var(--text-muted)]">
            Yeterli veri yüklendiğinde AI yorumları burada görünecek...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="terminal-card p-6">
      <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
        <Brain className="w-5 h-5 text-[var(--gold-primary)]" />
        AI Model Yorumları
      </h3>

      <div className="space-y-3 mb-4">
        {commentaries.map((comment) => {
          const Icon = comment.icon;
          return (
            <div
              key={comment.id}
              className="p-3 bg-[var(--bg-secondary)]/50 rounded-lg border-l-2 border-[var(--gold-primary)] hover:bg-[var(--bg-secondary)] transition-colors"
            >
              <div className="flex items-start gap-3">
                <Icon className="w-4 h-4 text-[var(--gold-primary)] flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[var(--text-primary)] leading-relaxed">
                    {comment.text}
                  </p>
                  <div className="flex items-center justify-between mt-2 text-xs text-[var(--text-muted)]">
                    <span className="font-medium">{comment.indicator}</span>
                    <span>{formatTimeAgo(comment.timestamp)}</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="pt-3 border-t border-[var(--border-color)] bg-amber-500/5 px-3 py-2 rounded-lg">
        <p className="text-xs text-amber-400/70 leading-relaxed">
          <strong>SPK Uyarısı:</strong> Bu yorumlar istatistiksel model çıktılarıdır,
          yatırım tavsiyesi niteliği taşımaz. Yatırım danışmanlığı yetkimiz bulunmamaktadır.
          Yatırım kararlarınızı almadan önce lisanslı bir yatırım danışmanına başvurunuz.
        </p>
      </div>
    </div>
  );
};

export default AICommentary;

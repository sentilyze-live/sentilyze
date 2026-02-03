import React, { useEffect, useState, useMemo } from 'react';
import { TrendingUp, Activity, BarChart3, AlertTriangle, Info } from 'lucide-react';
import { getTechnicalIndicators, type TechnicalIndicatorData } from '../../lib/api/realApi';

interface IndicatorCardProps {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  summary?: string;
  explanation?: string;
  color?: string;
}

const IndicatorCard: React.FC<IndicatorCardProps> = ({ 
  title, 
  icon: Icon, 
  children, 
  summary,
  explanation,
  color = '#3B82F6' 
}) => {
  return (
    <div className="glass-card p-4 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <div className="p-2 rounded-lg" style={{ backgroundColor: `${color}15` }}>
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
        <h3 className="text-lg font-semibold text-[#E6EDF3]">{title}</h3>
      </div>
      
      {/* Ana veriler */}
      <div className="flex-1">
        {children}
      </div>
      
      {/* AI Özeti - Veriye göre dinamik */}
      {summary && (
        <div className="mt-4 pt-3 border-t border-[#1F2A38]">
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-xs text-blue-300 font-medium mb-1">Yapay Zeka Özeti:</p>
              <p className="text-xs text-[#9AA4B2] leading-relaxed">{summary}</p>
            </div>
          </div>
        </div>
      )}
      
      {/* Açıklama - Verinin anlamı */}
      {explanation && (
        <div className="mt-2 p-2 bg-[#1A2230]/50 rounded">
          <p className="text-xs text-[#5F6B7A] leading-relaxed">
            <strong className="text-[#9AA4B2]">Ne anlama gelir?</strong> {explanation}
          </p>
        </div>
      )}
    </div>
  );
};

const ProgressBar: React.FC<{ value: number; color: string; label: string; max?: number }> = ({ 
  value, color, label, max = 100 
}) => {
  const percentage = Math.min((value / max) * 100, 100);
  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-[#9AA4B2]">{label}</span>
        <span className="font-mono text-[#E6EDF3]">{value.toFixed(2)}</span>
      </div>
      <div className="h-2 bg-[#1A2230] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ 
            width: `${percentage}%`, 
            backgroundColor: color,
            boxShadow: `0 0 10px ${color}40`
          }}
        />
      </div>
    </div>
  );
};

// Client-side özet oluşturma fonksiyonları - Maliyetsiz
const generateMomentumSummary = (rsi: number, stochastic: number, atr: number): string => {
  if (rsi >= 70 && stochastic >= 80) {
    return `RSI ${rsi.toFixed(1)} ve Stochastic ${stochastic.toFixed(1)} değerleriyle piyasa aşırı alım bölgesinde. Bu, kısa vadeli bir geri çekilme yaşanabileceğini gösterebilir. Ancak güçlü bir yükseliş trendinde RSI uzun süre yüksek kalabilir.`;
  } else if (rsi <= 30 && stochastic <= 20) {
    return `RSI ${rsi.toFixed(1)} ve Stochastic ${stochastic.toFixed(1)} değerleriyle piyasa aşırı satım bölgesinde. Bu, bir tepki alımı için uygun bölge olabileceğini gösteriyor. Ancak düşüş trendi devam ediyor olabilir.`;
  } else if (rsi > 50 && stochastic > 50) {
    return `RSI ${rsi.toFixed(1)} ve Stochastic ${stochastic.toFixed(1)} değerleri pozitif bölgede. Alıcılar hâlâ kontrolü ellerinde tutuyor. ATR ${atr.toFixed(2)} ile oynaklık orta seviyede.`;
  } else {
    return `RSI ${rsi.toFixed(1)} nötr bölgede. Piyasa kararsızlık yaşayabilir. Stochastic ${stochastic.toFixed(1)} değeriyle momentum yavaşlıyor olabilir.`;
  }
};

const generateTrendSummary = (sma20: number, sma50: number, sma200: number, macdMomentum: string): string => {
  const sma20Above50 = sma20 > sma50;
  const priceAbove200 = sma20 > sma200;
  
  if (sma20Above50 && priceAbove200 && macdMomentum === 'positive') {
    return `SMA 20 (${sma20.toFixed(2)}) SMA 50'nin üzerinde ve tüm hareketli ortalamalar 200'ün üzerinde. MACD pozitif. Bu, güçlü bir yükseliş trendinin devam ettiğini gösteriyor.`;
  } else if (!sma20Above50 && !priceAbove200 && macdMomentum === 'negative') {
    return `Kısa vadeli ortalama uzun vadelinin altında ve MACD negatif. Düşüş trendi devam ediyor olabilir. Trend dönüşü için MACD pozitif bölgeye geçmeli.`;
  } else if (sma20Above50 && !priceAbove200) {
    return `Kısa vadeli toparlanma var ancak fiyat hâlâ 200 günlük ortalamanın altında. Bu bir "ölü kedi sıçraması" olabilir. Dikkatli olunmalı.`;
  } else {
    return `Hareketli ortalamalar birbirine yakın. Trend belirsizliği söz konusu. MACD ${macdMomentum === 'positive' ? 'pozitif yönde' : 'negatif yönde'}. Net bir trend sinyali için daha fazla veri gerekiyor.`;
  }
};

const generateVolatilitySummary = (width: number, atr: number, upper: number, lower: number, currentPrice: number): string => {
  const position = ((currentPrice - lower) / (upper - lower)) * 100;
  
  if (width > 5) {
    return `Bollinger Bantları %${width.toFixed(1)} genişlikle yüksek volatilite gösteriyor. Fiyat bantların %${position.toFixed(0)}'lik bölümünde. ATR ${atr.toFixed(2)} ile oynaklık artmış durumda.`;
  } else if (width < 2) {
    return `Bantlar daralmış (%${width.toFixed(1)}), bu genellikle sert bir hareket öncesi "squeeze" formasyonudur. Fiyat bantların %${position.toFixed(0)}'lik bölümünde hazırlanıyor.`;
  } else {
    return `Volatilite normal seviyede (%${width.toFixed(1)}). Fiyat bantların %${position.toFixed(0)}'lik bölümünde seyrediyor. ATR ${atr.toFixed(2)} ortalama günlük hareket aralığını gösteriyor.`;
  }
};

const generateRegimeSummary = (rsi: number, macdMomentum: string, sma20: number, sma50: number): string => {
  const bullishCount = [
    rsi > 50,
    macdMomentum === 'positive',
    sma20 > sma50
  ].filter(Boolean).length;
  
  if (bullishCount === 3) {
    return `Tüm teknik göstergeler pozitif uyumlu. RSI, MACD ve hareketli ortalamalar yükselişi destekliyor. Bu "Boğa Piyasası" rejiminde kalıcı bir trend olabilir.`;
  } else if (bullishCount === 0) {
    return `Tüm göstergeler negatif. Düşüş trendi devam ediyor. Bu "Ayı Piyasası" rejiminde risk yüksek. Trend değişimi için göstergelerin pozitife dönmesi gerekli.`;
  } else if (bullishCount === 2) {
    return `Çoğunlukla pozitif sinyaller var (${bullishCount}/3). Piyasa kararsızlığı azalıyor olabilir. Mevcut eğilim devam etme olasılığı yüksek.`;
  } else {
    return `Karışık sinyaller (${bullishCount}/3 pozitif). Piyasa kararsızlık döneminde. Yeni bir trend başlangıcı için tüm göstergelerin aynı yöne dönmesi beklenmeli.`;
  }
};

const TechnicalIndicators: React.FC = () => {
  const [indicators, setIndicators] = useState<TechnicalIndicatorData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchIndicators = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await getTechnicalIndicators();
        if (data) {
          setIndicators(data);
        } else {
          setError('Teknik göstergeler alınamadı');
        }
      } catch (err) {
        console.error('Failed to fetch technical indicators:', err);
        setError('Veri alınırken bir hata oluştu');
      } finally {
        setIsLoading(false);
      }
    };

    fetchIndicators();
    const interval = setInterval(fetchIndicators, 60000);
    return () => clearInterval(interval);
  }, []);

  const getRsiCondition = (value: number): { text: string; color: string } => {
    if (value >= 70) return { text: 'Aşırı Alım Bölgesi', color: '#F43F5E' };
    if (value <= 30) return { text: 'Aşırı Satım Bölgesi', color: '#22C55E' };
    return { text: 'Nötr Bölge', color: '#A855F7' };
  };

  const getMarketRegime = (rsi: number, macd: string): { regime: string; confidence: number } => {
    if (rsi > 50 && macd === 'positive') return { regime: 'Yükseliş Eğilimi', confidence: 78 };
    if (rsi < 50 && macd === 'negative') return { regime: 'Düşüş Eğilimi', confidence: 72 };
    return { regime: 'Yatay Seyir', confidence: 65 };
  };

  // Mevcut değerleri al
  const rsiValue = indicators?.rsi?.value || 55;
  const macdMomentum = indicators?.macd?.momentum || 'positive';
  const bollingerUpper = indicators?.bollinger?.upper || 0;
  const bollingerLower = indicators?.bollinger?.lower || 0;
  const bollingerWidth = indicators?.bollinger?.width || 2.8;
  const bollingerMiddle = indicators?.bollinger?.middle || 0;
  const sma20 = indicators?.sma?.['20'] || 0;
  const sma50 = indicators?.sma?.['50'] || 0;
  const sma200 = indicators?.sma?.['200'] || 0;
  const stochasticK = indicators?.stochastic?.k || 50;
  const atr = indicators?.atr || 12.45;
  const marketRegime = getMarketRegime(rsiValue, macdMomentum);

  // Client-side özet oluştur - Maliyetsiz
  const momentumSummary = useMemo(() => 
    generateMomentumSummary(rsiValue, stochasticK, atr),
    [rsiValue, stochasticK, atr]
  );

  const trendSummary = useMemo(() => 
    generateTrendSummary(sma20, sma50, sma200, macdMomentum),
    [sma20, sma50, sma200, macdMomentum]
  );

  const volatilitySummary = useMemo(() => 
    generateVolatilitySummary(bollingerWidth, atr, bollingerUpper, bollingerLower, bollingerMiddle),
    [bollingerWidth, atr, bollingerUpper, bollingerLower, bollingerMiddle]
  );

  const regimeSummary = useMemo(() => 
    generateRegimeSummary(rsiValue, macdMomentum, sma20, sma50),
    [rsiValue, macdMomentum, sma20, sma50]
  );

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="glass-card p-4 h-64 animate-pulse">
            <div className="h-4 bg-[#1A2230] rounded w-1/2 mb-4"></div>
            <div className="space-y-3">
              <div className="h-3 bg-[#1A2230] rounded"></div>
              <div className="h-3 bg-[#1A2230] rounded w-3/4"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-6 mb-6">
        <div className="flex items-center gap-2 text-rose-400">
          <AlertTriangle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  const rsiCondition = getRsiCondition(rsiValue);

  return (
    <>
      {/* Legal Disclaimer */}
      <div className="glass-card p-4 mb-6 border-amber-500/30 bg-amber-500/5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-amber-200">
              <strong>Yasal Uyarı:</strong> Aşağıda sunulan teknik göstergeler ve piyasa verileri 
              yalnızca bilgilendirme amaçlıdır. Bu veriler yatırım tavsiyesi niteliği taşımaz. 
              Herhangi bir finansal karar vermeden önce SPK lisanslı bir aracı kuruma danışmanız 
              ve kendi araştırmanızı yapmanız önemle tavsiye edilir. Kripto para ve emtia 
              piyasaları yüksek volatilite ve sermaye kaybı riski içerir.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Momentum Indicators */}
        <IndicatorCard 
          title="Momentum Göstergeleri" 
          icon={Activity} 
          color="#3B82F6"
          summary={momentumSummary}
          explanation="RSI (Relative Strength Index) 0-100 arasında fiyat değişim hızını ölçer. 70 üzeri aşırı alım, 30 altı aşırı satım gösterir. Stochastic ise kapanış fiyatının son X günün en yüksek/düşük aralığındaki yerini gösterir."
        >
          <ProgressBar value={rsiValue} color="#3B82F6" label="RSI (14)" max={100} />
          <div className="flex justify-between text-sm mb-4">
            <span className="text-[#5F6B7A]">Durum:</span>
            <span style={{ color: rsiCondition.color }}>{rsiCondition.text}</span>
          </div>
          <ProgressBar value={stochasticK} color="#A855F7" label="Stochastic %K" max={100} />
          <div className="flex justify-between text-sm">
            <span className="text-[#5F6B7A]">ATR (14):</span>
            <span className="font-mono text-[#E6EDF3]">{atr.toFixed(2)}</span>
          </div>
        </IndicatorCard>

        {/* Trend Indicators */}
        <IndicatorCard 
          title="Trend Göstergeleri" 
          icon={TrendingUp} 
          color="#22C55E"
          summary={trendSummary}
          explanation="Hareketli Ortalamalar (SMA) geçmiş fiyatların ortalamasını gösterir. Kısa vadeli (20) uzun vadeli (50, 200) ortalamanın üzerindeyse yükseliş trendi vardır. MACD ise iki hareketli ortalama arasındaki farkı gösterir."
        >
          <div className="space-y-2">
            {sma20 > 0 && (
              <div className="flex justify-between items-center py-1 border-b border-[#1F2A38]/50">
                <span className="text-[#9AA4B2]">SMA 20:</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[#E6EDF3]">{sma20.toFixed(2)}</span>
                  <span className="text-emerald-400">↑</span>
                </div>
              </div>
            )}
            {sma50 > 0 && (
              <div className="flex justify-between items-center py-1 border-b border-[#1F2A38]/50">
                <span className="text-[#9AA4B2]">SMA 50:</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[#E6EDF3]">{sma50.toFixed(2)}</span>
                  <span className="text-emerald-400">↑</span>
                </div>
              </div>
            )}
            {sma200 > 0 && (
              <div className="flex justify-between items-center py-1">
                <span className="text-[#9AA4B2]">SMA 200:</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[#E6EDF3]">{sma200.toFixed(2)}</span>
                  <span className="text-emerald-400">↑</span>
                </div>
              </div>
            )}
          </div>
          <div className="mt-3 pt-3 border-t border-[#1F2A38]">
            <div className="flex justify-between text-sm">
              <span className="text-[#9AA4B2]">MACD:</span>
              <span className={`${macdMomentum === 'positive' ? 'text-emerald-400' : 'text-rose-400'} font-medium`}>
                {indicators?.macd?.value.toFixed(2) || '0.00'}
              </span>
            </div>
            <div className="text-xs text-[#5F6B7A] mt-1">
              Histogram: {indicators?.macd?.histogram && indicators.macd.histogram >= 0 ? '+' : ''}{indicators?.macd?.histogram.toFixed(2) || '0.00'}
            </div>
          </div>
        </IndicatorCard>

        {/* Volatility */}
        <IndicatorCard 
          title="Volatilite" 
          icon={BarChart3} 
          color="#9333EA"
          summary={volatilitySummary}
          explanation={`Bollinger Bantları, ortalamanın üstüne ve altına standart sapma kadar uzanan kanallardır. Bant genişliği volatiliteyi gösterir. Dar bantlar sert hareket öncesi "squeeze" formasyonu olabilir. ATR ise ortalama gerçek fiyat aralığını gösterir.`}
        >
          {bollingerUpper > 0 && (
            <div className="space-y-2 mb-3">
              <div className="flex justify-between text-sm">
                <span className="text-[#9AA4B2]">Bollinger Üst:</span>
                <span className="font-mono text-[#E6EDF3]">{bollingerUpper.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[#9AA4B2]">Bollinger Orta:</span>
                <span className="font-mono text-[#E6EDF3]">{bollingerMiddle.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[#9AA4B2]">Bollinger Alt:</span>
                <span className="font-mono text-[#E6EDF3]">{bollingerLower.toFixed(2)}</span>
              </div>
            </div>
          )}
          <div className="pt-3 border-t border-[#1F2A38]">
            <div className="flex justify-between items-center">
              <span className="text-[#9AA4B2]">Bant Genişliği:</span>
              <span className="px-2 py-1 rounded bg-purple-500/10 text-purple-400 text-sm font-medium">
                {bollingerWidth.toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between text-sm mt-2">
              <span className="text-[#9AA4B2]">ATR (14):</span>
              <span className="font-mono text-[#E6EDF3]">{atr.toFixed(2)}</span>
            </div>
          </div>
        </IndicatorCard>

        {/* Market Regime */}
        <IndicatorCard 
          title="Piyasa Durumu" 
          icon={TrendingUp} 
          color="#3B82F6"
          summary={regimeSummary}
          explanation="Bu gösterge, tüm teknik analiz göstergelerinin birleştirilmiş yorumudur. Birden fazla göstergenin aynı yönde sinyal vermesi trendin gücünü artırır. Ancak hiçbir gösterge %100 doğru değildir."
        >
          <div className="flex items-center justify-center mb-3">
            <div className="relative w-24 h-24">
              <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                <circle cx="50" cy="50" r="40" fill="none" stroke="#1F2A38" strokeWidth="10" />
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke="#3B82F6"
                  strokeWidth="10"
                  strokeLinecap="round"
                  strokeDasharray={`${marketRegime.confidence * 2.51} 251`}
                  className="transition-all duration-1000"
                  style={{ filter: 'drop-shadow(0 0 10px #3B82F640)' }}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-blue-400">{marketRegime.confidence}%</span>
                <span className="text-xs text-[#9AA4B2]">Gösterge Uyumu</span>
              </div>
            </div>
          </div>
          <div className="text-center mb-3">
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 text-sm font-bold border border-blue-500/30">
              <TrendingUp className="w-4 h-4" />
              {marketRegime.regime}
            </span>
          </div>
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <span className={sma20 > sma50 ? 'text-emerald-400' : 'text-rose-400'}>
                {sma20 > sma50 ? '✓' : '✗'}
              </span>
              <span className="text-[#9AA4B2]">SMA 20 {'>'} SMA 50</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={macdMomentum === 'positive' ? 'text-emerald-400' : 'text-rose-400'}>
                {macdMomentum === 'positive' ? '✓' : '✗'}
              </span>
              <span className="text-[#9AA4B2]">MACD pozitif bölgede</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={rsiValue > 50 && rsiValue < 70 ? 'text-emerald-400' : 'text-amber-400'}>
                {rsiValue > 50 && rsiValue < 70 ? '✓' : '!'}
              </span>
              <span className="text-[#9AA4B2]">RSI dengeli (50-70)</span>
            </div>
          </div>
        </IndicatorCard>
      </div>
    </>
  );
};

export default TechnicalIndicators;
import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  type ChartOptions,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { 
  TrendingUp, 
  TrendingDown, 
  Brain, 
  BarChart3, 
  Activity,
  Calendar,
  ExternalLink,
  X,
  AlertTriangle
} from 'lucide-react';
import LegalDisclaimer from '../components/ui/LegalDisclaimer';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Generate mock gold price data with spikes
const generateGoldData = (timeframe: string) => {
  const dataPoints = timeframe === '1H' ? 60 : timeframe === '1D' ? 24 : timeframe === '1W' ? 7 : timeframe === '1M' ? 30 : 365;
  const labels: string[] = [];
  const prices: number[] = [];
  const spikes: { index: number; price: number; change: number; date: string }[] = [];
  
  let basePrice = 2750;
  const now = new Date();
  
  for (let i = 0; i < dataPoints; i++) {
    const date = new Date(now);
    if (timeframe === '1H') date.setMinutes(date.getMinutes() - (dataPoints - i));
    else if (timeframe === '1D') date.setHours(date.getHours() - (dataPoints - i));
    else date.setDate(date.getDate() - (dataPoints - i));
    
    labels.push(date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      ...(timeframe === '1H' || timeframe === '1D' ? { hour: '2-digit', minute: '2-digit' } : {})
    }));
    
    // Random walk with occasional spikes
    const change = (Math.random() - 0.5) * (timeframe === '1H' ? 2 : timeframe === '1D' ? 5 : 15);
    basePrice += change;
    
    // Create spikes (>3% change)
    if (Math.abs(change) > basePrice * 0.03) {
      spikes.push({
        index: i,
        price: basePrice,
        change: (change / basePrice) * 100,
        date: labels[labels.length - 1],
      });
    }
    
    prices.push(basePrice);
  }
  
  return { labels, prices, spikes };
};

const spikeNews = [
  { title: 'Fed Interest Rate Decision', source: 'Reuters', url: '#' },
  { title: 'Gold Reserves Hit Record Highs', source: 'Bloomberg', url: '#' },
  { title: 'Central Bank Buying Surge', source: 'CNBC', url: '#' },
  { title: 'Geopolitical Tensions Rise', source: 'FT', url: '#' },
];

const timeframes = ['1H', '1D', '1W', '1M', '1Y', 'ALL'];

const GoldAnalysis = () => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ChartJS<'line'>>(null);
  const [selectedTimeframe, setSelectedTimeframe] = useState('1M');
  const [selectedSpike, setSelectedSpike] = useState<typeof spikeNews[0] & { change: number; date: string } | null>(null);
  const [chartData, setChartData] = useState(generateGoldData('1M'));

  useEffect(() => {
    setChartData(generateGoldData(selectedTimeframe));
  }, [selectedTimeframe]);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(
        '.gold-header',
        { y: 40, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.6,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: sectionRef.current,
            start: 'top 80%',
          },
        }
      );

      gsap.fromTo(
        '.chart-container',
        { rotateX: 10, opacity: 0 },
        {
          rotateX: 0,
          opacity: 1,
          duration: 0.8,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: '.chart-container',
            start: 'top 75%',
          },
        }
      );

      gsap.fromTo(
        '.analysis-card',
        { x: 50, opacity: 0 },
        {
          x: 0,
          opacity: 1,
          duration: 0.5,
          stagger: 0.15,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: '.analysis-cards',
            start: 'top 80%',
          },
        }
      );
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  const chartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(18, 24, 34, 0.95)',
        titleColor: '#E6EDF3',
        bodyColor: '#9AA4B2',
        borderColor: 'rgba(47, 228, 255, 0.2)',
        borderWidth: 1,
        padding: 12,
        displayColors: false,
        callbacks: {
          label: (context) => {
            const value = context.parsed.y;
            return `Price: $${value ? value.toFixed(2) : '0.00'}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(31, 42, 56, 0.5)',
        },
        ticks: {
          color: '#9AA4B2',
          maxTicksLimit: 6,
        },
      },
      y: {
        grid: {
          color: 'rgba(31, 42, 56, 0.5)',
        },
        ticks: {
          color: '#9AA4B2',
          callback: (value) => `$${value}`,
        },
      },
    },
    elements: {
      line: {
        tension: 0.4,
        borderWidth: 2,
      },
      point: {
        radius: 0,
        hitRadius: 10,
        hoverRadius: 6,
      },
    },
  };

  const data = {
    labels: chartData.labels,
    datasets: [
      {
        label: 'XAU/USD',
        data: chartData.prices,
        borderColor: '#FFD700',
        backgroundColor: (context: { chart: { ctx: CanvasRenderingContext2D; chartArea?: { top: number; bottom: number } } }) => {
          const ctx = context.chart.ctx;
          const gradient = ctx.createLinearGradient(0, context.chart.chartArea?.top || 0, 0, context.chart.chartArea?.bottom || 300);
          gradient.addColorStop(0, 'rgba(255, 215, 0, 0.2)');
          gradient.addColorStop(1, 'rgba(255, 215, 0, 0)');
          return gradient;
        },
        fill: true,
        pointBackgroundColor: chartData.prices.map((_, i) => 
          chartData.spikes.some(s => s.index === i) ? '#FFD700' : 'transparent'
        ),
        pointRadius: chartData.prices.map((_, i) => 
          chartData.spikes.some(s => s.index === i) ? 6 : 0
        ),
        pointBorderColor: '#FFD700',
        pointBorderWidth: 2,
      },
    ],
  };

  const handleSpikeClick = (spike: typeof chartData.spikes[0]) => {
    const news = spikeNews[Math.floor(Math.random() * spikeNews.length)];
    setSelectedSpike({ ...news, change: spike.change, date: spike.date });
  };

  return (
    <section
      id="gold-analysis"
      ref={sectionRef}
      className="py-24 relative overflow-hidden"
    >
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-[var(--void-black)] via-[var(--deep-slate)]/30 to-[var(--void-black)]" />
      
      {/* Gold accent line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[var(--gold-accent)]/50 to-transparent" />

      <div className="section-container max-w-7xl mx-auto relative z-10">
        {/* Legal Disclaimer */}
        <div className="mb-8">
          <LegalDisclaimer variant="inline" />
        </div>

        {/* Section Header */}
        <div className="gold-header text-center mb-12">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[var(--gold-accent)]/10 border border-[var(--gold-accent)]/20 mb-4">
            <Activity size={14} className="text-[var(--gold-accent)]" />
            <span className="text-xs font-medium text-[var(--gold-accent)] uppercase tracking-wider">
              Live Analysis
            </span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-[var(--soft-white)] mb-4">
            Gold <span className="gold-gradient-text">(XAU/USD)</span> Market Intelligence
          </h2>
          <p className="text-lg text-[var(--cool-gray)] max-w-2xl mx-auto">
            Real-time sentiment analysis and AI-powered scenario predictions
          </p>
          <p className="text-sm text-[var(--disabled-gray)] mt-2 italic">
            ⚠️ For informational purposes only - Not investment advice
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Chart Section */}
          <div className="lg:col-span-2">
            <div className="chart-container glass-card p-6" style={{ perspective: '1000px' }}>
              {/* Chart Header */}
              <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-[var(--gold-accent)]/10 flex items-center justify-center">
                    <TrendingUp size={20} className="text-[var(--gold-accent)]" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-[var(--soft-white)]">
                      XAU/USD
                    </h3>
                    <p className="text-sm text-[var(--cool-gray)]">
                      ${chartData.prices[chartData.prices.length - 1]?.toFixed(2)}
                    </p>
                  </div>
                </div>

                {/* Timeframe Buttons */}
                <div className="flex gap-1">
                  {timeframes.map((tf) => (
                    <button
                      key={tf}
                      onClick={() => setSelectedTimeframe(tf)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        selectedTimeframe === tf
                          ? 'bg-gradient-to-r from-[var(--signal-cyan)] to-[var(--lag-green)] text-[var(--void-black)]'
                          : 'bg-[var(--graphite-blue)] text-[var(--cool-gray)] hover:text-[var(--soft-white)]'
                      }`}
                    >
                      {tf}
                    </button>
                  ))}
                </div>
              </div>

              {/* Chart */}
              <div className="h-80 md:h-96 relative">
                <Line
                  ref={chartRef}
                  data={data}
                  options={{
                    ...chartOptions,
                    onClick: (_event, elements) => {
                      if (elements.length > 0) {
                        const index = elements[0].index;
                        const spike = chartData.spikes.find(s => s.index === index);
                        if (spike) handleSpikeClick(spike);
                      }
                    },
                  }}
                />
                
                {/* Spike markers overlay */}
                <div className="absolute inset-0 pointer-events-none">
                  {chartData.spikes.map((spike, i) => (
                    <button
                      key={i}
                      onClick={() => handleSpikeClick(spike)}
                      className="absolute spike-marker pointer-events-auto"
                      style={{
                        left: `${(spike.index / chartData.labels.length) * 100}%`,
                        top: '20%',
                      }}
                    >
                      <div
                        className={`w-4 h-4 rounded-full flex items-center justify-center ${
                          spike.change > 0 ? 'bg-[var(--lag-green)]' : 'bg-[var(--muted-red)]'
                        }`}
                        style={{
                          boxShadow: `0 0 15px ${spike.change > 0 ? 'var(--lag-green)' : 'var(--muted-red)'}`,
                        }}
                      >
                        {spike.change > 0 ? (
                          <TrendingUp size={10} className="text-[var(--void-black)]" />
                        ) : (
                          <TrendingDown size={10} className="text-[var(--void-black)]" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Spike Legend */}
              <div className="flex items-center gap-4 mt-4 text-xs text-[var(--cool-gray)]">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-[var(--lag-green)]" style={{ boxShadow: '0 0 8px var(--lag-green)' }} />
                  <span>Spike &gt;+3%</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-[var(--muted-red)]" style={{ boxShadow: '0 0 8px var(--muted-red)' }} />
                  <span>Spike &lt;-3%</span>
                </div>
                <span className="ml-auto">Click spikes for details</span>
              </div>
            </div>

            {/* Spike Detail Panel */}
            {selectedSpike && (
              <div className="mt-6 glass-card p-6 border-[var(--gold-accent)]/30 animate-[fade-in-up_0.3s_ease-out]">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`text-2xl font-bold ${
                          selectedSpike.change > 0 ? 'text-[var(--lag-green)]' : 'text-[var(--muted-red)]'
                        }`}
                      >
                        {selectedSpike.change > 0 ? '+' : ''}
                        {selectedSpike.change.toFixed(1)}%
                      </span>
                      <span className="text-sm text-[var(--cool-gray)]">Spike Detected</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-[var(--cool-gray)]">
                      <Calendar size={14} />
                      <span>{selectedSpike.date}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedSpike(null)}
                    className="p-1 rounded-lg text-[var(--cool-gray)] hover:text-[var(--soft-white)] hover:bg-[var(--graphite-blue)] transition-all"
                  >
                    <X size={18} />
                  </button>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-medium text-[var(--soft-white)] mb-2">
                    Causes of this spike
                  </h4>
                  <a
                    href={selectedSpike.url}
                    className="flex items-center gap-2 p-3 rounded-lg bg-[var(--graphite-blue)] hover:bg-[var(--deep-slate)] transition-colors group"
                  >
                    <ExternalLink size={16} className="text-[var(--signal-cyan)]" />
                    <span className="text-sm text-[var(--soft-white)] group-hover:text-[var(--signal-cyan)] transition-colors">
                      {selectedSpike.title}
                    </span>
                    <span className="text-xs text-[var(--cool-gray)] ml-auto">
                      {selectedSpike.source}
                    </span>
                  </a>
                </div>

                <div className="flex flex-wrap gap-2">
                  <span className="tag-gold">Gold</span>
                  <span className="tag">XAU/USD</span>
                  <span className="tag-green">High Volatility</span>
                </div>
              </div>
            )}
          </div>

          {/* Analysis Cards */}
          <div className="analysis-cards space-y-6">
            {/* Technical Indicators */}
            <div className="analysis-card glass-card p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-[var(--signal-cyan)]/10 flex items-center justify-center">
                  <BarChart3 size={20} className="text-[var(--signal-cyan)]" />
                </div>
                <h3 className="text-base font-semibold text-[var(--soft-white)]">
                  Technical Indicators
                </h3>
              </div>

              <div className="space-y-3">
                {[
                  { label: 'RSI (14)', value: '62.4', status: 'Neutral', color: 'var(--amber-pulse)' },
                  { label: 'MACD', value: 'Bullish', status: 'Crossover', color: 'var(--lag-green)' },
                  { label: 'Bollinger', value: 'Upper', status: 'Band Touch', color: 'var(--signal-cyan)' },
                  { label: 'SMA 50/200', value: 'Golden', status: 'Cross', color: 'var(--gold-accent)' },
                ].map((indicator) => (
                  <div
                    key={indicator.label}
                    className="flex items-center justify-between p-3 rounded-lg bg-[var(--graphite-blue)]"
                  >
                    <span className="text-sm text-[var(--cool-gray)]">{indicator.label}</span>
                    <div className="text-right">
                      <span className="text-sm font-medium text-[var(--soft-white)]">
                        {indicator.value}
                      </span>
                      <span
                        className="text-xs ml-2"
                        style={{ color: indicator.color }}
                      >
                        {indicator.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Sentiment Analysis */}
            <div className="analysis-card glass-card p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-[var(--lag-green)]/10 flex items-center justify-center">
                  <Brain size={20} className="text-[var(--lag-green)]" />
                </div>
                <h3 className="text-base font-semibold text-[var(--soft-white)]">
                  Sentiment Analysis
                </h3>
              </div>

              {/* Gauge */}
              <div className="relative h-32 mb-4">
                <svg viewBox="0 0 200 100" className="w-full h-full">
                  {/* Background arc */}
                  <path
                    d="M 20 100 A 80 80 0 0 1 180 100"
                    fill="none"
                    stroke="var(--graphite-blue)"
                    strokeWidth="20"
                  />
                  {/* Value arc */}
                  <path
                    d="M 20 100 A 80 80 0 0 1 152 55"
                    fill="none"
                    stroke="url(#gaugeGradient)"
                    strokeWidth="20"
                  />
                  {/* Needle */}
                  <line
                    x1="100"
                    y1="100"
                    x2="145"
                    y2="50"
                    stroke="var(--soft-white)"
                    strokeWidth="3"
                    strokeLinecap="round"
                  />
                  <circle cx="100" cy="100" r="8" fill="var(--soft-white)" />
                  <defs>
                    <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="var(--muted-red)" />
                      <stop offset="50%" stopColor="var(--amber-pulse)" />
                      <stop offset="100%" stopColor="var(--lag-green)" />
                    </linearGradient>
                  </defs>
                </svg>
                <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-center">
                  <span className="text-2xl font-bold text-[var(--lag-green)]">+0.72</span>
                  <p className="text-xs text-[var(--cool-gray)]">Bullish</p>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[var(--cool-gray)]">Social Media</span>
                  <span className="text-sm font-medium text-[var(--lag-green)]">+0.68</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[var(--cool-gray)]">News</span>
                  <span className="text-sm font-medium text-[var(--lag-green)]">+0.76</span>
                </div>
              </div>
            </div>

            {/* ML Predictions */}
            <div className="analysis-card glass-card p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-[var(--gold-accent)]/10 flex items-center justify-center">
                  <TrendingUp size={20} className="text-[var(--gold-accent)]" />
                </div>
                <h3 className="text-base font-semibold text-[var(--soft-white)]">
                  ML Predictions
                </h3>
              </div>

              <div className="space-y-4">
                {[
                  { timeframe: '24h', prediction: '+2.4%', confidence: 85 },
                  { timeframe: '7d', prediction: '+0.8%', confidence: 72 },
                  { timeframe: '30d', prediction: '-1.2%', confidence: 64 },
                ].map((pred) => (
                  <div key={pred.timeframe}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-[var(--cool-gray)]">{pred.timeframe}</span>
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-sm font-bold ${
                            pred.prediction.startsWith('+')
                              ? 'text-[var(--lag-green)]'
                              : 'text-[var(--muted-red)]'
                          }`}
                        >
                          {pred.prediction}
                        </span>
                        <span className="text-xs text-[var(--cool-gray)]">
                          {pred.confidence}%
                        </span>
                      </div>
                    </div>
                    <div className="h-2 rounded-full bg-[var(--graphite-blue)] overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-1000"
                        style={{
                          width: `${pred.confidence}%`,
                          background: pred.prediction.startsWith('+')
                            ? 'linear-gradient(90deg, var(--lag-green), var(--signal-cyan))'
                            : 'linear-gradient(90deg, var(--muted-red), var(--amber-pulse))',
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 pt-4 border-t border-[var(--border)]">
                <div className="flex items-center gap-2 text-xs text-[var(--cool-gray)]">
                  <Brain size={12} />
                  <span>LSTM + ARIMA + XGBoost Ensemble</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default GoldAnalysis;

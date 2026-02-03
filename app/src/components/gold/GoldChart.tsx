import React, { useEffect, useRef, useState } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, BarController, Title, Tooltip, Legend, Filler } from 'chart.js';
import { Chart } from 'react-chartjs-2';
import { getGoldHistory } from '../../lib/api/realApi';
import { formatTurkishNumber } from '../../lib/utils/format';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, BarController, Title, Tooltip, Legend, Filler);

interface ChartData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

const GoldChart: React.FC = () => {
  const chartRef = useRef<ChartJS | null>(null);
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [timeframe, setTimeframe] = useState('1D');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const history = await getGoldHistory(timeframe);
        if (history && history.prices) {
          setChartData(history.prices);
        }
      } catch (error) {
        console.error('Failed to fetch chart data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [timeframe]);

  const labels = chartData.map(d => new Date(d.timestamp).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }));

  const chartDatasets = [
    {
      type: 'line' as const,
      label: 'Fiyat',
      data: chartData.map(d => d.close),
      borderColor: '#3B82F6',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      borderWidth: 2,
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      pointHoverRadius: 6,
      pointHoverBackgroundColor: '#3B82F6',
      pointHoverBorderColor: '#0B0F14',
      pointHoverBorderWidth: 2,
      yAxisID: 'y',
    },
    {
      type: 'bar' as const,
      label: 'Hacim',
      data: chartData.map(d => d.volume),
      backgroundColor: 'rgba(147, 51, 234, 0.3)',
      borderColor: '#9333EA',
      borderWidth: 1,
      yAxisID: 'y1',
      barThickness: 2,
    },
  ];

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index' as const, intersect: false },
    plugins: {
      legend: { position: 'top' as const, align: 'end' as const, labels: { color: '#9AA4B2', font: { size: 12 }, usePointStyle: true, pointStyle: 'circle', boxWidth: 8 } },
      tooltip: {
        backgroundColor: '#121822', titleColor: '#3B82F6', bodyColor: '#E6EDF3', borderColor: '#1F2A38', borderWidth: 1, padding: 12, displayColors: true,
        callbacks: {
          label: (context: { dataset: { label?: string }; parsed: { y: number } }) => {
            const label = context.dataset.label || '';
            return label ? `${label}: ${formatTurkishNumber(context.parsed.y)}` : '';
          },
        },
      },
    },
    scales: {
      x: { grid: { color: '#1F2A38', drawBorder: false }, ticks: { color: '#5F6B7A', font: { size: 11 }, maxTicksLimit: 10 } },
      y: { type: 'linear' as const, display: true, position: 'left' as const, grid: { color: '#1F2A38', drawBorder: false }, ticks: { color: '#5F6B7A', font: { size: 11 } } },
      y1: { type: 'linear' as const, display: true, position: 'right' as const, grid: { drawOnChartArea: false }, ticks: { display: false } },
    },
  };

  const timeframes = [
    { label: '1dk', value: '1D' },
    { label: '1H', value: '1D' },
    { label: '1g', value: '1W' },
    { label: '1h', value: '1M' },
    { label: '1y', value: '1Y' },
  ];

  return (
    <div className="glass-card p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-blue-400 flex items-center gap-2">
          <span className="text-2xl">📊</span> XAU/USD GRAFİĞİ
        </h2>
        <div className="flex gap-2">
          {timeframes.map((tf) => (
            <button
              key={tf.value}
              onClick={() => setTimeframe(tf.value)}
              className={`px-3 py-1 rounded text-sm font-medium transition-all duration-200 ${timeframe === tf.value ? 'bg-blue-500 text-white' : 'bg-[#1A2230] text-[#9AA4B2] hover:bg-purple-500/10 hover:text-purple-400'}`}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>
      <div className="h-[400px] w-full">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <span className="text-[#9AA4B2]">Veriler yükleniyor...</span>
          </div>
        ) : chartData.length > 0 ? (
          <Chart ref={chartRef} type="line" data={{ labels, datasets: chartDatasets }} options={options} />
        ) : (
          <div className="flex items-center justify-center h-full">
            <span className="text-[#9AA4B2]">Veri bulunamadı</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default GoldChart;

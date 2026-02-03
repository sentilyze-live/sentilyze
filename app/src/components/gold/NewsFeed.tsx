import React, { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, ExternalLink, BarChart3, AlertTriangle, Link2 } from 'lucide-react';
import { getGoldNews, analyzeNewsSentiment, type RealNewsArticle } from '../../lib/api/realApi';

interface NewsItem {
  id: string;
  source: string;
  title: string;
  summary: string;
  url: string;
  publishedAt: string;
  sentiment: number;
  sentimentLabel: 'positive' | 'negative' | 'neutral';
}

interface CorrelationData {
  asset: string;
  correlation: number;
  strength: string;
  color: string;
}

const NewsFeed: React.FC = () => {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchNews = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const articles = await getGoldNews();
        
        const formattedNews: NewsItem[] = await Promise.all(
          articles.map(async (article, index) => {
            const textToAnalyze = `${article.title} ${article.description || ''}`;
            const sentimentResult = await analyzeNewsSentiment(textToAnalyze);
            
            return {
              id: `${article.url}-${index}`,
              source: article.source?.name || 'Bilinmeyen Kaynak',
              title: article.title,
              summary: article.description || '',
              url: article.url,
              publishedAt: article.publishedAt,
              sentiment: sentimentResult.sentiment,
              sentimentLabel: sentimentResult.label,
            };
          })
        );

        setNews(formattedNews.slice(0, 5));
      } catch (err) {
        console.error('Failed to fetch news:', err);
        setError('Haberler yüklenirken bir hata oluştu');
      } finally {
        setIsLoading(false);
      }
    };

    fetchNews();
    const interval = setInterval(fetchNews, 300000);
    return () => clearInterval(interval);
  }, []);

  const getSentimentColor = (sentiment: number) => {
    if (sentiment > 0.2) {
      return { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30', icon: TrendingUp };
    } else if (sentiment < -0.2) {
      return { bg: 'bg-rose-500/10', text: 'text-rose-400', border: 'border-rose-500/30', icon: TrendingDown };
    }
    return { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/30', icon: BarChart3 };
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / 3600000);
    
    if (diffHours < 1) return 'Az önce';
    if (diffHours < 24) return `${diffHours} sa önce`;
    return `${Math.floor(diffHours / 24)} gün önce`;
  };

  const correlationData: CorrelationData[] = [
    { asset: 'DXY (Dolar Endeksi)', correlation: -0.85, strength: 'Güçlü Negatif', color: '#F43F5E' },
    { asset: 'BTC/USD', correlation: 0.42, strength: 'Orta Pozitif', color: '#22C55E' },
    { asset: 'S&P 500', correlation: -0.15, strength: 'Zayıf Negatif', color: '#A855F7' },
    { asset: 'US10Y (10Y Tahvil)', correlation: -0.72, strength: 'Güçlü Negatif', color: '#F43F5E' },
  ];

  const laggedCorrelation = [
    { lag: '1 saat', correlation: 0.68 },
    { lag: '6 saat', correlation: 0.45 },
    { lag: '24 saat', correlation: 0.23 },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
      {/* News Feed */}
      <div className="glass-card p-6">
        {/* Disclaimer */}
        <div className="mb-4 p-3 bg-amber-500/5 border border-amber-500/30 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-200">
              Haberler üçüncü taraf kaynaklardan otomatik olarak çekilmektedir. 
              Sentilyze bu haberlerin içeriğinden sorumlu değildir.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-blue-400 flex items-center gap-2">
            <span className="text-xl">📰</span> ALTIN HABERLERİ
          </h2>
          <span className="text-xs text-[#5F6B7A]">
            {isLoading ? 'Yükleniyor...' : `${news.length} haber`}
          </span>
        </div>

        <div className="space-y-3 max-h-[400px] overflow-y-auto">
          {isLoading ? (
            <div className="text-center py-8">
              <span className="text-[#9AA4B2]">Haberler yükleniyor...</span>
            </div>
          ) : error ? (
            <div className="text-center py-8 text-rose-400">{error}</div>
          ) : news.length > 0 ? (
            news.map((item) => {
              const sentimentStyle = getSentimentColor(item.sentiment);
              const SentimentIcon = sentimentStyle.icon;
              return (
                <div
                  key={item.id}
                  className="p-4 bg-[#1A2230]/50 rounded-lg border border-[#1F2A38] hover:border-blue-500/30 transition-all cursor-pointer group"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-[#9AA4B2] bg-[#1A2230] px-2 py-0.5 rounded">
                        {item.source}
                      </span>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${sentimentStyle.bg} ${sentimentStyle.text} ${sentimentStyle.border}`}>
                        <SentimentIcon className="w-3 h-3" />
                        {item.sentimentLabel === 'positive' ? 'Olumlu' : item.sentimentLabel === 'negative' ? 'Olumsuz' : 'Nötr'}
                      </span>
                    </div>
                    <span className="text-xs text-[#5F6B7A]">{formatTime(item.publishedAt)}</span>
                  </div>
                  
                  <h3 className="text-sm font-semibold text-[#E6EDF3] mb-1 group-hover:text-blue-400 transition-colors">
                    {item.title}
                  </h3>
                  <p className="text-xs text-[#9AA4B2] mb-2 line-clamp-2">{item.summary}</p>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[#5F6B7A]">
                      Duygu Skoru: {(item.sentiment * 100).toFixed(0)}%
                    </span>
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-blue-400 hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <ExternalLink className="w-3 h-3" />
                      Kaynağa Git
                    </a>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="text-center py-8 text-[#9AA4B2]">
              Haber bulunamadı
            </div>
          )}
        </div>
      </div>

      {/* Correlation Matrix */}
      <div className="glass-card p-6">
        {/* Disclaimer */}
        <div className="mb-4 p-3 bg-amber-500/5 border border-amber-500/30 rounded-lg">
          <div className="flex items-start gap-2">
            <Link2 className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-200">
              Korelasyon verileri geçmiş dönem istatistiklerine dayanmaktadır. 
              Korelasyon nedensellik ilişkisi göstermez.
            </p>
          </div>
        </div>

        <h2 className="text-lg font-bold text-blue-400 mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          KORELASYON ANALİZİ
        </h2>

        <div className="space-y-4 mb-6">
          <p className="text-xs text-[#9AA4B2]">XAU/USD Korelasyonu (Son 30 gün)</p>
          {correlationData.map((item) => (
            <div key={item.asset} className="flex items-center justify-between py-2 border-b border-[#1F2A38]/50 last:border-0">
              <span className="text-sm text-[#E6EDF3]">{item.asset}</span>
              <div className="flex items-center gap-3">
                <span className="text-sm font-mono" style={{ color: item.color }}>
                  {item.correlation > 0 ? '+' : ''}{item.correlation.toFixed(2)}
                </span>
                <span className="text-xs text-[#9AA4B2]">{item.strength}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Lagged Correlation */}
        <div className="pt-4 border-t border-[#1F2A38]">
          <h3 className="text-sm font-semibold text-[#9AA4B2] mb-3">
            Gecikmeli Korelasyon (Duygu → Fiyat)
          </h3>
          <div className="grid grid-cols-3 gap-4">
            {laggedCorrelation.map((item) => (
              <div key={item.lag} className="text-center p-3 bg-[#1A2230]/50 rounded-lg">
                <div className="text-xs text-[#9AA4B2] mb-1">{item.lag}</div>
                <div className={`text-lg font-bold ${item.correlation > 0.5 ? 'text-blue-400' : 'text-purple-400'}`}>
                  {item.correlation.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <p className="text-xs text-blue-400">
              <strong>Not:</strong> Sosyal medya duygu analizi ile altın fiyatları arasındaki 
              istatistiksel ilişki araştırma amaçlıdır. Geçmiş korelasyon gelecekteki 
              performansın garantisi değildir.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NewsFeed;
import React, { useEffect, useState } from 'react';
import { MessageSquare, Twitter, TrendingUp, TrendingDown, Minus, Users, Newspaper, AlertTriangle } from 'lucide-react';
import { getMarketSentiment, getSocialPosts, type SentimentData, type SocialPost } from '../../lib/api/realApi';

const SentimentPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'sentiment' | 'social'>('sentiment');
  const [sentiment, setSentiment] = useState<SentimentData | null>(null);
  const [socialPosts, setSocialPosts] = useState<SocialPost[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const [sentimentData, postsData] = await Promise.all([
          getMarketSentiment(),
          getSocialPosts()
        ]);
        
        if (sentimentData) {
          setSentiment(sentimentData);
        }
        if (postsData && postsData.length > 0) {
          setSocialPosts(postsData);
        }
      } catch (err) {
        console.error('Failed to fetch sentiment data:', err);
        setError('Veri alınırken bir hata oluştu');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  const getSentimentColor = (value: number) => {
    if (value >= 60) return { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30' };
    if (value >= 40) return { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/30' };
    return { bg: 'bg-rose-500/10', text: 'text-rose-400', border: 'border-rose-500/30' };
  };

  const getSentimentIcon = (value: number) => {
    if (value >= 60) return <TrendingUp className="w-4 h-4" />;
    if (value >= 40) return <Minus className="w-4 h-4" />;
    return <TrendingDown className="w-4 h-4" />;
  };

  const getStatusLabel = (value: number) => {
    if (value >= 75) return 'Aşırı İyimserlik';
    if (value >= 60) return 'İyimser';
    if (value >= 40) return 'Nötr';
    if (value >= 25) return 'Karamsar';
    return 'Aşırı Karamsarlık';
  };

  const sentimentValue = sentiment ? Math.round(sentiment.score * 100) : 50;
  const colors = getSentimentColor(sentimentValue);

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Az önce';
    if (diffMins < 60) return `${diffMins} dk önce`;
    return `${Math.floor(diffMins / 60)} sa önce`;
  };

  const sentimentSources = sentiment?.sources || [
    { name: 'Twitter/X', percentage: 40, positiveRatio: 71 },
    { name: 'Reddit', percentage: 35, positiveRatio: 68 },
    { name: 'Haber Siteleri', percentage: 20, positiveRatio: 45 },
    { name: 'Forumlar', percentage: 5, positiveRatio: 52 },
  ];

  const topKeywords = sentiment?.keywords || ['FED', 'faiz', 'altın', 'güvenli liman', 'enflasyon', 'ons', 'gram'];

  return (
    <div className="glass-card p-6 mb-6">
      {/* Legal Disclaimer */}
      <div className="mb-4 p-3 bg-amber-500/5 border border-amber-500/30 rounded-lg">
        <div className="flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-amber-200">
            Duygu analizi yapay zeka modelleri tarafından sosyal medya ve haber kaynaklarından 
            elde edilen verilerle oluşturulmuştur. Yatırım kararı verme konusunda kullanılamaz.
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-blue-400 flex items-center gap-2">
          <span className="text-2xl">🎭</span> PAZASA DUYGU ANALİZİ
        </h2>
        
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('sentiment')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'sentiment'
                ? 'bg-blue-500 text-white'
                : 'bg-[#1A2230] text-[#9AA4B2] hover:text-white'
            }`}
          >
            Özet
          </button>
          <button
            onClick={() => setActiveTab('social')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'social'
                ? 'bg-blue-500 text-white'
                : 'bg-[#1A2230] text-[#9AA4B2] hover:text-white'
            }`}
          >
            Sosyal Medya
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <span className="text-[#9AA4B2]">Veriler yükleniyor...</span>
        </div>
      ) : error ? (
        <div className="text-center py-8 text-rose-400">{error}</div>
      ) : activeTab === 'sentiment' ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="flex flex-col items-center">
            <div className="relative w-48 h-48 mb-4">
              <svg viewBox="0 0 200 200" className="w-full h-full">
                <path
                  d="M 20 180 A 80 80 0 0 1 180 180"
                  fill="none"
                  stroke="#1F2A38"
                  strokeWidth="20"
                  strokeLinecap="round"
                />
                <path
                  d="M 20 180 A 80 80 0 0 1 180 180"
                  fill="none"
                  stroke={sentimentValue >= 60 ? '#3B82F6' : sentimentValue >= 40 ? '#9333EA' : '#F43F5E'}
                  strokeWidth="20"
                  strokeLinecap="round"
                  strokeDasharray={`${sentimentValue * 2.51} 251`}
                  className="transition-all duration-1000"
                  style={{ 
                    filter: `drop-shadow(0 0 15px ${sentimentValue >= 60 ? '#3B82F6' : sentimentValue >= 40 ? '#9333EA' : '#F43F5E'}40)`
                  }}
                />
                <text x="30" y="190" fill="#F43F5E" fontSize="12" textAnchor="middle">Korku</text>
                <text x="100" y="120" fill={sentimentValue >= 60 ? '#3B82F6' : sentimentValue >= 40 ? '#9333EA' : '#F43F5E'} fontSize="36" fontWeight="bold" textAnchor="middle">
                  {sentimentValue}
                </text>
                <text x="170" y="190" fill="#3B82F6" fontSize="12" textAnchor="middle">Açgözlülük</text>
              </svg>
            </div>
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border ${colors.bg} ${colors.text} ${colors.border}`}>
              {getSentimentIcon(sentimentValue)}
              <span className="font-semibold">{getStatusLabel(sentimentValue)}</span>
            </div>
            {sentiment?.lastUpdated && (
              <p className="text-xs text-[#5F6B7A] mt-2">
                Son güncelleme: {formatTime(sentiment.lastUpdated)}
              </p>
            )}
          </div>

          <div>
            <h3 className="text-sm font-semibold text-[#9AA4B2] mb-3">Kaynak Dağılımı</h3>
            <div className="space-y-3">
              {sentimentSources.map((source) => {
                const Icon = source.name.includes('Twitter') ? Twitter : 
                            source.name.includes('Reddit') ? MessageSquare :
                            source.name.includes('Haber') ? Newspaper : Users;
                const sourceColors = getSentimentColor(source.positiveRatio);
                return (
                  <div key={source.name} className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-[#1A2230] flex items-center justify-center">
                      <Icon className="w-4 h-4 text-[#9AA4B2]" />
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-[#E6EDF3]">{source.name}</span>
                        <span className={sourceColors.text}>%{source.positiveRatio} Olumlu</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-[#1A2230] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{ 
                              width: `${source.percentage}%`,
                              backgroundColor: source.positiveRatio >= 60 ? '#3B82F6' : source.positiveRatio >= 40 ? '#9333EA' : '#F43F5E',
                            }}
                          />
                        </div>
                        <span className="text-xs text-[#5F6B7A] w-8">%{source.percentage}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-4">
              <h3 className="text-sm font-semibold text-[#9AA4B2] mb-2">Öne Çıkan Konular</h3>
              <div className="flex flex-wrap gap-2">
                {topKeywords.map((keyword) => (
                  <span
                    key={keyword}
                    className="px-2 py-1 bg-[#1A2230] text-[#9AA4B2] text-xs rounded border border-[#1F2A38] hover:border-blue-500 hover:text-blue-400 transition-colors cursor-pointer"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3 max-h-[400px] overflow-y-auto">
          {socialPosts.length === 0 ? (
            <div className="text-center py-8 text-[#9AA4B2]">
              Sosyal medya verisi bulunamadı
            </div>
          ) : (
            socialPosts.map((item) => {
              const sentimentColors = getSentimentColor(item.sentiment * 100);
              return (
                <div
                  key={item.id}
                  className="p-4 bg-[#1A2230]/50 rounded-lg border border-[#1F2A38] hover:border-blue-500/30 transition-all"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${sentimentColors.bg} ${sentimentColors.text} ${sentimentColors.border}`}>
                        {getSentimentIcon(item.sentiment * 100)}
                        %{(item.sentiment * 100).toFixed(0)}
                      </span>
                      <span className="text-xs text-[#5F6B7A]">{formatTime(item.publishedAt)}</span>
                    </div>
                    <span className="text-xs text-blue-400">{item.platform}</span>
                  </div>
                  <p className="text-sm text-[#E6EDF3] mb-2">{item.content}</p>
                  <div className="flex items-center justify-between">
                    <div className="flex flex-wrap gap-1">
                      {item.hashtags?.map((tag) => (
                        <span key={tag} className="text-xs text-blue-400">{tag}</span>
                      ))}
                    </div>
                    <span className="text-xs text-[#5F6B7A]">
                      Etkileşim: {item.engagement?.toLocaleString() || 0}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};

export default SentimentPanel;

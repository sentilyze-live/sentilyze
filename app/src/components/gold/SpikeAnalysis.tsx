import React, { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Calendar, ChevronDown, ChevronUp, Download, History, AlertTriangle } from 'lucide-react';
import { getVolatilityEvents, type VolatilityEvent } from '../../lib/api/realApi';

const SpikeAnalysis: React.FC = () => {
  const [events, setEvents] = useState<VolatilityEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'up' | 'down'>('all');

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await getVolatilityEvents();
        if (data && data.length > 0) {
          setEvents(data);
        }
      } catch (err) {
        console.error('Failed to fetch volatility events:', err);
        setError('Volatilite verileri alınamadı');
      } finally {
        setIsLoading(false);
      }
    };

    fetchEvents();
    const interval = setInterval(fetchEvents, 300000);
    return () => clearInterval(interval);
  }, []);

  const filteredEvents = filter === 'all' 
    ? events
    : events.filter(e => filter === 'up' ? e.direction === 'up' : e.direction === 'down');

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' });
  };

  const getSeverityLabel = (severity: string) => {
    switch (severity) {
      case 'high': return 'Yüksek';
      case 'medium': return 'Orta';
      case 'low': return 'Düşük';
      default: return severity;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'text-rose-400 bg-rose-500/20';
      case 'medium': return 'text-amber-400 bg-amber-500/20';
      case 'low': return 'text-emerald-400 bg-emerald-500/20';
      default: return 'text-[#9AA4B2] bg-[#1A2230]';
    }
  };

  return (
    <div className="glass-card p-6 mb-6">
      {/* Legal Disclaimer */}
      <div className="mb-6 p-3 bg-amber-500/5 border border-amber-500/30 rounded-lg">
        <div className="flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-amber-200">
            Aşağıdaki veriler geçmiş volatilite olaylarını göstermektedir. Geçmiş performans 
            gelecekteki sonuçların göstergesi değildir. Piyasa koşulları değişkenlik gösterebilir.
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-blue-400 flex items-center gap-2">
            <History className="w-6 h-6" />
            TARİHSEL VOLATİLİTE ANALİZİ
          </h2>
          <p className="text-xs text-[#5F6B7A] mt-1">
            Önemli fiyat hareketleri ve tetikleyici faktörler
          </p>
        </div>
        
        <div className="flex gap-2">
          {[
            { key: 'all', label: 'Tümü' },
            { key: 'up', label: 'Yükseliş' },
            { key: 'down', label: 'Düşüş' },
          ].map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key as 'all' | 'up' | 'down')}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                filter === f.key
                  ? 'bg-blue-500 text-white'
                  : 'bg-[#1A2230] text-[#9AA4B2] hover:text-white'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-8">
          <span className="text-[#9AA4B2]">Veriler yükleniyor...</span>
        </div>
      ) : error ? (
        <div className="text-center py-8 text-rose-400">{error}</div>
      ) : filteredEvents.length === 0 ? (
        <div className="text-center py-8 text-[#9AA4B2]">
          Belirtilen kriterlere uygun volatilite olayı bulunamadı
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {filteredEvents.map((event) => {
              const isExpanded = expandedId === event.id;
              const isPositive = event.direction === 'up';
              
              return (
                <div
                  key={event.id}
                  className={`border rounded-lg transition-all duration-300 ${
                    isPositive 
                      ? 'bg-blue-500/5 border-blue-500/20' 
                      : 'bg-rose-500/5 border-rose-500/20'
                  } ${isExpanded ? 'border-opacity-50' : ''}`}
                >
                  <div
                    className="p-4 cursor-pointer flex items-center justify-between"
                    onClick={() => setExpandedId(isExpanded ? null : event.id)}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-lg ${isPositive ? 'bg-blue-500/20' : 'bg-rose-500/20'}`}>
                        {isPositive ? (
                          <TrendingUp className="w-5 h-5 text-blue-400" />
                        ) : (
                          <TrendingDown className="w-5 h-5 text-rose-400" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[#9AA4B2] text-sm">
                            <Calendar className="w-3 h-3 inline mr-1" />
                            {formatDate(event.timestamp)}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                            isPositive 
                              ? 'bg-blue-500/20 text-blue-400' 
                              : 'bg-rose-500/20 text-rose-400'
                          }`}>
                            {isPositive ? '+' : ''}{event.changePercent.toFixed(1)}%
                          </span>
                          <span className={`px-2 py-0.5 rounded text-xs ${getSeverityColor(event.severity)}`}>
                            {getSeverityLabel(event.severity)} Etki
                          </span>
                        </div>
                        <h3 className="text-[#E6EDF3] font-semibold mt-1">
                          {event.triggers[0] || 'Piyasa Hareketi'}
                        </h3>
                        <p className="text-sm text-[#9AA4B2]">
                          {event.priceBefore.toLocaleString()} → {event.priceAfter.toLocaleString()} USD
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <button 
                        className="p-2 rounded-lg bg-[#1A2230] text-[#9AA4B2] hover:text-blue-400 transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          // Export functionality
                        }}
                      >
                        <Download className="w-4 h-4" />
                      </button>
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-[#9AA4B2]" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-[#9AA4B2]" />
                      )}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="px-4 pb-4">
                      <div className="border-t border-[#1F2A38] pt-4">
                        <p className="text-sm text-[#E6EDF3] mb-4">
                          {event.marketContext || 
                            `Bu volatilite olayı ${event.triggers.join(', ')} etkisiyle gerçekleşmiştir.`}
                        </p>
                        
                        <div className="space-y-2">
                          <p className="text-xs text-[#9AA4B2] font-semibold">Tetikleyici Faktörler:</p>
                          <div className="flex flex-wrap gap-2">
                            {event.triggers.map((trigger, idx) => (
                              <span
                                key={idx}
                                className="px-3 py-1.5 bg-blue-500/10 text-blue-400 text-xs rounded-lg"
                              >
                                {trigger}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                          <div className="bg-[#1A2230]/50 p-3 rounded">
                            <span className="text-[#9AA4B2]">Önceki Fiyat:</span>
                            <p className="font-mono text-[#E6EDF3]">{event.priceBefore.toLocaleString()} USD</p>
                          </div>
                          <div className="bg-[#1A2230]/50 p-3 rounded">
                            <span className="text-[#9AA4B2]">Sonraki Fiyat:</span>
                            <p className="font-mono text-[#E6EDF3]">{event.priceAfter.toLocaleString()} USD</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="mt-4 pt-4 border-t border-[#1F2A38] text-center">
            <button className="text-sm text-blue-400 hover:underline inline-flex items-center gap-1">
              <History className="w-4 h-4" />
              Tüm tarihsel verileri görüntüle
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default SpikeAnalysis;
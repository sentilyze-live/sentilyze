import React, { useEffect, useState } from 'react';
import { Bell, Share2, Star } from 'lucide-react';
import { getRealGoldPrice } from '../../lib/api/realApi';

interface GoldPriceData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  high24h: number;
  low24h: number;
  open24h: number;
  timestamp: string;
  source: string;
}

const GoldHeader: React.FC = () => {
  const [price, setPrice] = useState<GoldPriceData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchPrice = async () => {
      try {
        setIsLoading(true);
        const data = await getRealGoldPrice();
        if (data) {
          setPrice(data);
        }
      } catch (error) {
        console.error('Failed to fetch gold price:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPrice();
    const interval = setInterval(fetchPrice, 30000);
    return () => clearInterval(interval);
  }, []);

  const isPositive = price ? price.change >= 0 : true;
  const displayPrice = price?.price || 2450.30;
  const displayChange = price?.change || 15.40;
  const displayChangePercent = price?.changePercent || 0.63;

  const formatTurkishNumber = (num: number) => {
    return num.toLocaleString('tr-TR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  return (
    <header className="sticky top-0 z-40 bg-gradient-to-r from-[#0B0F14] via-[#121822] to-[#0B0F14] border-b border-[#1F2A38]">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-extrabold text-blue-400 tracking-tight">
                  {isLoading ? (
                    <span className="animate-pulse">...</span>
                  ) : (
                    formatTurkishNumber(displayPrice)
                  )}
                </span>
                <span className="text-lg text-[#9AA4B2]">USD</span>
              </div>
              <div className="flex items-center gap-3 mt-1">
                <span className={`text-lg font-semibold ${isPositive ? 'text-blue-400' : 'text-rose-400'}`}>
                  {isPositive ? '+' : ''}{formatTurkishNumber(displayChange)} ({isPositive ? '+' : ''}{formatTurkishNumber(displayChangePercent)}%)
                </span>
                <span className="text-sm text-[#5F6B7A]">
                  24s Yüksek: <span className="text-blue-400">{formatTurkishNumber(price?.high24h || 2465.20)}</span> | 
                  Düşük: <span className="text-rose-400">{formatTurkishNumber(price?.low24h || 2432.10)}</span>
                </span>
              </div>
              <div className="text-xs text-[#5F6B7A] mt-1">
                Son güncelleme: {price?.timestamp ? new Date(price.timestamp).toLocaleTimeString('tr-TR') : new Date().toLocaleTimeString('tr-TR')} {price && `(${price.source})`}
              </div>
            </div>
          </div>

          <div className="hidden md:flex items-center">
            <svg width="200" height="60" className="opacity-80">
              <path
                d="M0,40 Q20,35 40,30 T80,25 T120,35 T160,30 T200,20"
                fill="none"
                stroke={isPositive ? "#60A5FA" : "#F43F5E"}
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>

          <div className="flex items-center gap-3">
            <button className="p-2 rounded-lg bg-[#1A2230] hover:bg-blue-500/10 hover:text-blue-400 text-[#9AA4B2] transition-all duration-200">
              <Star className="w-5 h-5" />
            </button>
            <button className="p-2 rounded-lg bg-[#1A2230] hover:bg-purple-500/10 hover:text-purple-400 text-[#9AA4B2] transition-all duration-200">
              <Bell className="w-5 h-5" />
            </button>
            <button className="p-2 rounded-lg bg-[#1A2230] hover:bg-blue-500/10 hover:text-blue-400 text-[#9AA4B2] transition-all duration-200">
              <Share2 className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default GoldHeader;

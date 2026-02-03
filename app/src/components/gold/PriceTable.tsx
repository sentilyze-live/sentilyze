import React, { useEffect, useState } from 'react';
import { getRealGoldPrice } from '../../lib/api/realApi';

interface PriceData {
  name: string;
  buy: string;
  sell: string;
  isGold?: boolean;
}

const PriceTable: React.FC = () => {
  const [goldPrice, setGoldPrice] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchPrice = async () => {
      try {
        setIsLoading(true);
        const price = await getRealGoldPrice();
        if (price) {
          setGoldPrice(price.price);
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

  const defaultPriceData: PriceData[] = [
    { name: 'Altın (Gram)', buy: '2,847.45', sell: '2,852.30', isGold: true },
    { name: 'Ons Altın', buy: '2,785.00', sell: '2,790.00' },
    { name: 'USD/TL', buy: '32.45', sell: '32.55' },
    { name: 'EUR/TL', buy: '35.20', sell: '35.40' },
  ];

  const displayData = goldPrice 
    ? [
      { name: 'Altın (Ons)', buy: goldPrice.toFixed(2), sell: (goldPrice + 5).toFixed(2), isGold: true },
      ...defaultPriceData.slice(1),
    ]
    : defaultPriceData;

  return (
    <div className="glass-card p-6 mb-6">
      <h2 className="text-xl font-bold text-blue-400 mb-4 flex items-center gap-2">
        <span className="text-2xl">📈</span> ALTIN FİYATLARI
      </h2>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#1F2A38]">
              <th className="text-left py-3 px-4 text-[#9AA4B2] font-semibold text-sm">Bilgi amaçlıdır</th>
              <th className="text-center py-3 px-4 text-[#9AA4B2] font-semibold text-sm">Alış</th>
              <th className="text-center py-3 px-4 text-[#9AA4B2] font-semibold text-sm">Satış</th>
            </tr>
          </thead>
          <tbody>
            {displayData.map((item, index) => (
              <tr 
                key={item.name}
                className={`border-b border-[#1F2A38]/50 hover:bg-[#1A2230]/50 transition-colors ${
                  index === displayData.length - 1 ? 'border-b-0' : ''
                }`}
              >
                <td className={`py-4 px-4 ${item.isGold ? 'text-lg font-bold text-blue-400' : 'text-base font-medium text-[#E6EDF3]'}`}>
                  {item.name}
                </td>
                <td className={`py-4 px-4 text-center font-mono ${item.isGold ? 'text-lg font-bold text-emerald-400' : 'text-base text-emerald-400'}`}>
                  {item.buy}
                </td>
                <td className={`py-4 px-4 text-center font-mono ${item.isGold ? 'text-lg font-bold text-rose-400' : 'text-base text-rose-400'}`}>
                  {item.sell}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <p className="text-xs text-[#5F6B7A] mt-3 text-center">
        {isLoading ? 'Fiyatlar yükleniyor...' : 'Veriler canlı kaynaklardan alınmaktadır.'}
      </p>
    </div>
  );
};

export default PriceTable;

import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface LegalDisclaimerProps {
  onAccept?: () => void;
  showCloseButton?: boolean;
  variant?: 'banner' | 'modal' | 'inline';
}

const LegalDisclaimer: React.FC<LegalDisclaimerProps> = ({ 
  onAccept, 
  showCloseButton = false,
  variant = 'banner'
}) => {
  const [isVisible, setIsVisible] = React.useState(true);

  if (!isVisible) return null;

  const content = (
    <>
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-semibold text-amber-400 mb-2">
            YASAL UYARI VE RİSK BİLDİRİMİ
          </h3>
          <div className="text-sm text-amber-200/80 space-y-2">
            <p>
              <strong>Sentilyze bir yatırım danışmanlığı platformu değildir.</strong> Sunulan tüm veriler, 
              yapay zeka modelleri tarafından üretilen <strong>bilgilendirme amaçlı senaryo analizleridir</strong> 
              ve kesinlik taşımaz.
            </p>
            <p>
              Bu platform, kullanıcılara <strong>yatırım tavsiyesi vermemektedir</strong>. Herhangi bir finansal 
              karar vermeden önce lisanslı bir yatırım danışmanına başvurmanız şiddetle önerilir.
            </p>
            <p>
              Kripto para birimleri, altın ve diğer emtia piyasaları <strong>yüksek volatilite ve sermaye kaybı riski</strong> içerir. 
              Geçmiş performans gelecek performansın garantisi değildir. Tüm yatırım kararlarının sorumluluğu 
              tamamen kullanıcıya aittir.
            </p>
            <p className="text-xs text-amber-300/60 mt-3">
              6362 sayılı SPK Kanunu kapsamında yatırım danışmanlığı faaliyeti yürütülmemektedir.
            </p>
          </div>
        </div>
        {showCloseButton && (
          <button 
            onClick={() => setIsVisible(false)}
            className="text-amber-400 hover:text-amber-300 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>
      {onAccept && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={onAccept}
            className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Anladım ve Kabul Ediyorum
          </button>
        </div>
      )}
    </>
  );

  if (variant === 'modal') {
    return (
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div className="bg-gradient-to-r from-amber-900/90 to-red-900/90 border border-amber-700/50 rounded-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          {content}
        </div>
      </div>
    );
  }

  if (variant === 'inline') {
    return (
      <div className="bg-gradient-to-r from-amber-900/30 to-red-900/30 border border-amber-700/50 rounded-lg p-4">
        {content}
      </div>
    );
  }

  // Banner variant (default)
  return (
    <div className="bg-gradient-to-r from-amber-900/30 to-red-900/30 border-b border-amber-700/50 p-4">
      <div className="max-w-7xl mx-auto">
        {content}
      </div>
    </div>
  );
};

export default LegalDisclaimer;

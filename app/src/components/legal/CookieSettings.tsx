import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Cookie, Shield, BarChart3, Target } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Switch } from '@/components/ui/switch';
import { useCookieConsent } from '@/hooks/useCookieConsent';

/**
 * Cookie Settings Modal
 * Granular control over cookie preferences (KVKK/GDPR compliant)
 */
const CookieSettings = () => {
  const {
    showSettings,
    necessary,
    analytics,
    marketing,
    updateConsent,
    closeSettings,
  } = useCookieConsent();

  // Local state for form
  const [preferences, setPreferences] = useState({
    necessary: true, // Always true
    analytics,
    marketing,
  });

  const handleSave = () => {
    updateConsent({
      analytics: preferences.analytics,
      marketing: preferences.marketing,
    });
  };

  const handleCancel = () => {
    // Reset to current values
    setPreferences({ necessary: true, analytics, marketing });
    closeSettings();
  };

  return (
    <Dialog open={showSettings} onOpenChange={(open) => !open && handleCancel()}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-2">
            <Cookie className="w-6 h-6 text-[var(--signal-cyan)]" />
            <DialogTitle className="text-xl">Çerez Ayarları</DialogTitle>
          </div>
          <DialogDescription className="text-[var(--text-secondary)]">
            Çerez tercihlerinizi özelleştirin. Gerekli çerezler sitenin çalışması için zorunludur
            ve devre dışı bırakılamaz.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Necessary Cookies */}
          <div className="flex items-start justify-between gap-4 p-4 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
            <div className="flex items-start gap-3 flex-1">
              <Shield className="w-5 h-5 text-[var(--signal-cyan)] flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="font-semibold text-[var(--text-primary)]">
                    Gerekli Çerezler
                  </h3>
                  <span className="text-xs px-2 py-1 rounded bg-[var(--signal-cyan)]/20 text-[var(--signal-cyan)]">
                    Her Zaman Aktif
                  </span>
                </div>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                  Bu çerezler web sitesinin düzgün çalışması için gereklidir. Tema tercihiniz ve
                  çerez onay durumunuz gibi temel bilgileri saklar.
                </p>
                <ul className="mt-2 text-xs text-[var(--text-muted)] space-y-1">
                  <li>• sentilyze-theme (1 yıl)</li>
                  <li>• sentilyze-cookie-consent (1 yıl)</li>
                </ul>
              </div>
            </div>
            <Switch
              checked={preferences.necessary}
              disabled
              aria-label="Gerekli çerezler her zaman aktif"
            />
          </div>

          {/* Analytics Cookies */}
          <div className="flex items-start justify-between gap-4 p-4 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
            <div className="flex items-start gap-3 flex-1">
              <BarChart3 className="w-5 h-5 text-[var(--lag-green)] flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-[var(--text-primary)] mb-1">
                  Analitik Çerezler
                </h3>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                  Platformumuzu nasıl kullandığınızı anlamamıza yardımcı olur. Bu veriler anonim
                  olarak toplanır ve kullanıcı deneyimini iyileştirmek için kullanılır.
                </p>
                <ul className="mt-2 text-xs text-[var(--text-muted)] space-y-1">
                  <li>• Google Analytics (_ga, _gid, _gat - 2 yıl)</li>
                </ul>
              </div>
            </div>
            <Switch
              checked={preferences.analytics}
              onCheckedChange={(checked) =>
                setPreferences((prev) => ({ ...prev, analytics: checked }))
              }
              aria-label="Analitik çerezleri aktif/pasif yap"
            />
          </div>

          {/* Marketing Cookies */}
          <div className="flex items-start justify-between gap-4 p-4 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
            <div className="flex items-start gap-3 flex-1">
              <Target className="w-5 h-5 text-[var(--text-muted)] flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-[var(--text-primary)] mb-1">
                  Pazarlama Çerezleri
                </h3>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                  Size özel reklamlar göstermek ve pazarlama kampanyalarının etkinliğini ölçmek
                  için kullanılır. Şu anda bu kategoride aktif çerez bulunmamaktadır.
                </p>
              </div>
            </div>
            <Switch
              checked={preferences.marketing}
              onCheckedChange={(checked) =>
                setPreferences((prev) => ({ ...prev, marketing: checked }))
              }
              aria-label="Pazarlama çerezleri aktif/pasif yap"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-[var(--border-color)] pt-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <Link
            to="/legal/cookies"
            className="text-sm text-[var(--signal-cyan)] hover:underline"
            onClick={closeSettings}
          >
            Çerez Politikasını Görüntüle
          </Link>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCancel}
              className="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            >
              İptal
            </button>
            <button
              onClick={handleSave}
              className="px-6 py-2 rounded-lg bg-gradient-to-r from-[var(--signal-cyan)] to-[var(--lag-green)] text-[var(--void-black)] font-semibold hover:scale-105 transition-transform text-sm"
            >
              Tercihleri Kaydet
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default CookieSettings;

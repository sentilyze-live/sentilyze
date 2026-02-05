import { useEffect, useRef } from 'react';
import { Cookie } from 'lucide-react';
import { gsap } from 'gsap';
import { useCookieConsent } from '@/hooks/useCookieConsent';

/**
 * KVKK/GDPR Compliant Cookie Consent Banner
 * Shows on first visit, persists preference across sessions
 */
const CookieConsent = () => {
  const {
    showBanner,
    acceptAll,
    rejectAll,
    openSettings,
  } = useCookieConsent();

  const bannerRef = useRef<HTMLDivElement>(null);

  // Slide-up animation on mount
  useEffect(() => {
    if (showBanner && bannerRef.current) {
      gsap.fromTo(
        bannerRef.current,
        { y: 100, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.4, ease: 'expo.out' }
      );
    }
  }, [showBanner]);

  if (!showBanner) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 backdrop-blur-[2px] z-[9998]"
        aria-hidden="true"
      />

      {/* Banner */}
      <div
        ref={bannerRef}
        className="fixed bottom-0 left-0 right-0 z-[9999] backdrop-blur-xl bg-[var(--bg-card)]/95 border-t border-[var(--border-color)] px-4 py-6 sm:px-6"
        style={{ boxShadow: '0 -4px 24px rgba(0, 0, 0, 0.3)' }}
        role="dialog"
        aria-labelledby="cookie-consent-title"
        aria-describedby="cookie-consent-description"
      >
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            {/* Icon & Content */}
            <div className="flex items-start gap-3 flex-1">
              <Cookie className="w-6 h-6 text-[var(--signal-cyan)] flex-shrink-0 mt-1" />
              <div>
                <h2
                  id="cookie-consent-title"
                  className="text-[var(--text-primary)] font-semibold mb-1"
                >
                  Çerez Tercihleri
                </h2>
                <p
                  id="cookie-consent-description"
                  className="text-sm text-[var(--text-secondary)] leading-relaxed"
                >
                  Deneyiminizi geliştirmek için çerezler kullanıyoruz. Tercihlerinizi özelleştirebilir
                  veya tümünü kabul/reddetebilirsiniz. Daha fazla bilgi için{' '}
                  <a
                    href="/legal/cookies"
                    className="text-[var(--signal-cyan)] hover:underline"
                    onClick={(e) => {
                      e.preventDefault();
                      window.location.href = '/legal/cookies';
                    }}
                  >
                    Çerez Politikamızı
                  </a>{' '}
                  inceleyebilirsiniz.
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
              <button
                onClick={openSettings}
                className="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors whitespace-nowrap"
                aria-label="Çerez tercihlerini özelleştir"
              >
                Özelleştir
              </button>
              <button
                onClick={rejectAll}
                className="px-6 py-2 rounded-lg border border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] transition-colors text-sm font-medium whitespace-nowrap"
                aria-label="Tüm isteğe bağlı çerezleri reddet"
              >
                Tümünü Reddet
              </button>
              <button
                onClick={acceptAll}
                className="px-6 py-2 rounded-lg bg-gradient-to-r from-[var(--signal-cyan)] to-[var(--lag-green)] text-[var(--void-black)] font-semibold hover:scale-105 transition-transform text-sm whitespace-nowrap"
                aria-label="Tüm çerezleri kabul et"
              >
                Tümünü Kabul Et
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default CookieConsent;

import type { CookieInfo, CookieConsent } from '@/types/cookies';

/**
 * Cookie Utilities
 * KVKK/GDPR compliant cookie management and script blocking
 */

export const STORAGE_KEY = 'sentilyze-cookie-consent';
export const CONSENT_VERSION = '1.0';

/**
 * Cookie definitions for transparency
 * Used in Cookie Policy page
 */
export const COOKIE_DEFINITIONS: CookieInfo[] = [
  {
    name: 'sentilyze-theme',
    category: 'necessary',
    provider: 'Sentilyze',
    purpose: 'Stores user theme preference (dark/light mode)',
    purposeTR: 'Kullanıcı tema tercihini saklar (karanlık/aydınlık mod)',
    expiry: '1 year',
  },
  {
    name: 'sentilyze-cookie-consent',
    category: 'necessary',
    provider: 'Sentilyze',
    purpose: 'Stores cookie consent preferences',
    purposeTR: 'Çerez izin tercihlerini saklar',
    expiry: '1 year',
  },
  {
    name: '_ga',
    category: 'analytics',
    provider: 'Google Analytics',
    purpose: 'Used to distinguish users for analytics',
    purposeTR: 'Analitik için kullanıcıları ayırt etmek amacıyla kullanılır',
    expiry: '2 years',
  },
  {
    name: '_gid',
    category: 'analytics',
    provider: 'Google Analytics',
    purpose: 'Used to distinguish users for analytics',
    purposeTR: 'Analitik için kullanıcıları ayırt etmek amacıyla kullanılır',
    expiry: '24 hours',
  },
  {
    name: '_gat',
    category: 'analytics',
    provider: 'Google Analytics',
    purpose: 'Used to throttle request rate',
    purposeTR: 'İstek oranını sınırlamak için kullanılır',
    expiry: '1 minute',
  },
];

/**
 * Get current cookie consent from localStorage
 */
export const getConsent = (): CookieConsent | null => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;

    const consent = JSON.parse(stored) as CookieConsent;

    // Check version - if mismatch, invalidate consent
    if (consent.version !== CONSENT_VERSION) {
      return null;
    }

    return consent;
  } catch (error) {
    console.error('Error reading cookie consent:', error);
    return null;
  }
};

/**
 * Save cookie consent to localStorage
 */
export const saveConsent = (consent: CookieConsent): void => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(consent));

    // Dispatch custom event for script loading
    window.dispatchEvent(new CustomEvent('cookieConsentGranted', {
      detail: {
        analytics: consent.analytics,
        marketing: consent.marketing,
      },
    }));
  } catch (error) {
    console.error('Error saving cookie consent:', error);
  }
};

/**
 * Check if analytics cookies are allowed
 */
export const shouldLoadAnalytics = (): boolean => {
  const consent = getConsent();
  return consent?.analytics ?? false;
};

/**
 * Check if marketing cookies are allowed
 */
export const shouldLoadMarketing = (): boolean => {
  const consent = getConsent();
  return consent?.marketing ?? false;
};

/**
 * Default consent state (opt-in by default - GDPR compliant)
 */
export const getDefaultConsent = (): CookieConsent => ({
  necessary: true,
  analytics: false,
  marketing: false,
  timestamp: Date.now(),
  version: CONSENT_VERSION,
});

/**
 * Block third-party scripts until consent is given
 * Call this function in index.html or App initialization
 */
export const blockScriptsUntilConsent = (): void => {
  // Listen for consent event
  window.addEventListener('cookieConsentGranted', (event) => {
    const detail = (event as CustomEvent).detail;

    // Load Google Analytics if analytics consent given
    if (detail.analytics && !window.gtag) {
      loadGoogleAnalytics();
    }

    // Load marketing scripts if marketing consent given
    if (detail.marketing) {
      loadMarketingScripts();
    }
  });

  // Check existing consent on page load
  const consent = getConsent();
  if (consent) {
    if (consent.analytics && !window.gtag) {
      loadGoogleAnalytics();
    }
    if (consent.marketing) {
      loadMarketingScripts();
    }
  }
};

/**
 * Load Google Analytics script dynamically
 */
const loadGoogleAnalytics = (): void => {
  // Replace GA_MEASUREMENT_ID with actual ID when available
  const GA_MEASUREMENT_ID = 'G-XXXXXXXXXX';

  // Create script element
  const script = document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`;
  document.head.appendChild(script);

  // Initialize gtag
  window.dataLayer = window.dataLayer || [];
  function gtag(...args: unknown[]) {
    window.dataLayer.push(args);
  }
  window.gtag = gtag;

  gtag('js', new Date());
  gtag('config', GA_MEASUREMENT_ID);
};

/**
 * Load marketing scripts dynamically
 */
const loadMarketingScripts = (): void => {
  // Add marketing/advertising scripts here when needed
  // Example: Facebook Pixel, LinkedIn Insight Tag, etc.
};

/**
 * Extend Window interface for gtag
 */
declare global {
  interface Window {
    dataLayer: unknown[];
    gtag: (...args: unknown[]) => void;
  }
}

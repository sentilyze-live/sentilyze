/**
 * Cookie Consent Types
 * KVKK/GDPR compliant cookie consent management
 */

export type CookieCategory = 'necessary' | 'analytics' | 'marketing';

export interface CookieConsent {
  necessary: boolean;        // Always true, cannot be disabled
  analytics: boolean;
  marketing: boolean;
  timestamp: number;
  version: string;          // For policy updates (current: '1.0')
}

export interface CookieConsentState extends CookieConsent {
  hasConsented: boolean;
  showBanner: boolean;
  showSettings: boolean;
}

export interface CookieInfo {
  name: string;
  category: CookieCategory;
  provider: string;
  purpose: string;
  purposeTR: string;        // Turkish translation
  expiry: string;
}

export interface CookieConsentActions {
  acceptAll: () => void;
  rejectAll: () => void;
  updateConsent: (consent: Partial<CookieConsent>) => void;
  openSettings: () => void;
  closeSettings: () => void;
  closeBanner: () => void;
}

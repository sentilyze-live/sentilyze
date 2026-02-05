import { useState, useEffect } from 'react';
import type { CookieConsent, CookieConsentState, CookieConsentActions } from '@/types/cookies';
import { getConsent, saveConsent, getDefaultConsent } from '@/lib/utils/cookies';

/**
 * Custom hook for cookie consent management
 * KVKK/GDPR compliant
 */
export const useCookieConsent = (): CookieConsentState & CookieConsentActions => {
  const [state, setState] = useState<CookieConsentState>(() => {
    const existing = getConsent();

    if (existing) {
      // User has already consented
      return {
        ...existing,
        hasConsented: true,
        showBanner: false,
        showSettings: false,
      };
    }

    // First visit - show banner
    return {
      ...getDefaultConsent(),
      hasConsented: false,
      showBanner: true,
      showSettings: false,
    };
  });

  /**
   * Accept all cookies
   */
  const acceptAll = () => {
    const consent: CookieConsent = {
      ...getDefaultConsent(),
      analytics: true,
      marketing: true,
    };

    saveConsent(consent);

    setState({
      ...consent,
      hasConsented: true,
      showBanner: false,
      showSettings: false,
    });
  };

  /**
   * Reject all non-necessary cookies
   */
  const rejectAll = () => {
    const consent = getDefaultConsent();

    saveConsent(consent);

    setState({
      ...consent,
      hasConsented: true,
      showBanner: false,
      showSettings: false,
    });
  };

  /**
   * Update consent with custom preferences
   */
  const updateConsent = (updates: Partial<CookieConsent>) => {
    const consent: CookieConsent = {
      necessary: true, // Always true
      analytics: updates.analytics ?? state.analytics,
      marketing: updates.marketing ?? state.marketing,
      timestamp: Date.now(),
      version: state.version,
    };

    saveConsent(consent);

    setState({
      ...consent,
      hasConsented: true,
      showBanner: false,
      showSettings: false,
    });
  };

  /**
   * Open settings modal
   */
  const openSettings = () => {
    setState(prev => ({
      ...prev,
      showSettings: true,
      showBanner: false,
    }));
  };

  /**
   * Close settings modal
   */
  const closeSettings = () => {
    setState(prev => ({
      ...prev,
      showSettings: false,
    }));
  };

  /**
   * Close banner (only after consent given)
   */
  const closeBanner = () => {
    if (state.hasConsented) {
      setState(prev => ({
        ...prev,
        showBanner: false,
      }));
    }
  };

  /**
   * Listen for storage changes (multi-tab sync)
   */
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'sentilyze-cookie-consent' && e.newValue) {
        try {
          const consent = JSON.parse(e.newValue) as CookieConsent;
          setState(prev => ({
            ...consent,
            hasConsented: true,
            showBanner: false,
            showSettings: prev.showSettings,
          }));
        } catch (error) {
          console.error('Error parsing cookie consent from storage event:', error);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  return {
    ...state,
    acceptAll,
    rejectAll,
    updateConsent,
    openSettings,
    closeSettings,
    closeBanner,
  };
};

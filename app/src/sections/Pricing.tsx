import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Check, X as XIcon, Sparkles, Zap, Crown, Rocket, AlertTriangle } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const features = [
  { name: 'Gold (XAU/USD) Analysis',  free: true,    starter: true,                    pro: true,              proPlus: true },
  { name: 'Crypto Analysis',          free: false,   starter: 'Top 5 (BTC, ETH...)',   pro: 'Top 20',         proPlus: 'Top 50+' },
  { name: 'Stocks / BIST',            free: false,   starter: false,                    pro: 'Top 30 + BIST',  proPlus: 'All Markets' },
  { name: 'Watchlist',                free: '1',     starter: '5',                      pro: '20',             proPlus: '50' },
  { name: 'AI Predictions',           free: '3/day', starter: '25/day',                 pro: 'Unlimited',      proPlus: 'Unlimited' },
  { name: 'Sentiment Score',          free: 'Basic', starter: 'Advanced',               pro: 'Advanced',       proPlus: 'Advanced+' },
  { name: 'Historical Data',          free: '7 days',starter: '90 days',                pro: '1 year',         proPlus: '5 years' },
  { name: 'Technical Indicators',     free: '2',     starter: '15+',                    pro: '30+',            proPlus: '50+' },
  { name: 'Email Alerts',             free: false,   starter: '10/day',                 pro: 'Unlimited',      proPlus: 'Unlimited' },
  { name: 'Telegram Alerts',          free: false,   starter: false,                    pro: true,             proPlus: true },
  { name: 'API Access',               free: false,   starter: false,                    pro: '5K/day',         proPlus: '50K/day' },
  { name: 'Backtesting',              free: false,   starter: false,                    pro: '90 days',        proPlus: '5 years' },
  { name: 'Webhooks',                 free: false,   starter: false,                    pro: false,            proPlus: true },
];

const trackPricingClick = (plan: string) => {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', 'pricing_click', {
      event_category: 'conversion',
      event_label: plan,
      value: plan === 'starter' ? 24.99 : plan === 'pro' ? 49.99 : plan === 'pro_plus' ? 99.99 : 0,
    });
  }
};

const Pricing = () => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [currency, setCurrency] = useState<'usd' | 'try'>('usd');

  const prices = {
    usd: { starter: '$24.99', pro: '$49.99', proPlus: '$99.99', starterYear: '$224', proYear: '$449', proPlusYear: '$899', saveSt: '$76', savePro: '$151', saveProPlus: '$301' },
    try: { starter: '\u20BA399', pro: '\u20BA849', proPlus: '\u20BA1,699', starterYear: '\u20BA3,588', proYear: '\u20BA7,641', proPlusYear: '\u20BA15,291', saveSt: '\u20BA1,200', savePro: '\u20BA2,547', saveProPlus: '\u20BA5,097' },
  };

  const p = prices[currency];

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(
        '.pricing-header',
        { y: 40, opacity: 0 },
        {
          y: 0, opacity: 1, duration: 0.6, ease: 'expo.out',
          scrollTrigger: { trigger: sectionRef.current, start: 'top 80%' },
        }
      );
      gsap.fromTo(
        '.pricing-card',
        { y: 30, opacity: 0 },
        {
          y: 0, opacity: 1, duration: 0.6, stagger: 0.12, ease: 'expo.out',
          scrollTrigger: { trigger: '.pricing-cards', start: 'top 75%' },
        }
      );
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  const renderValue = (value: boolean | string) => {
    if (value === true) return <Check size={16} className="text-[var(--lag-green)]" />;
    if (value === false) return <XIcon size={16} className="text-[var(--disabled-gray)]" />;
    return <span className="text-sm text-[var(--soft-white)]">{value}</span>;
  };

  return (
    <section id="pricing" ref={sectionRef} className="py-28 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-[var(--void-black)] via-[var(--deep-slate)]/20 to-[var(--void-black)]" />

      <div className="section-container max-w-7xl mx-auto relative z-10">
        <div className="pricing-header text-center mb-16">
          <span className="inline-block px-4 py-1.5 rounded-full bg-[var(--gold-accent)]/10 text-[var(--gold-accent)] text-xs font-medium uppercase tracking-wider mb-4">
            Pricing
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-[var(--soft-white)] mb-4">
            Choose Your Plan
          </h2>
          <p className="text-lg text-[var(--cool-gray)] max-w-2xl mx-auto mb-6">
            Start free and scale as you grow. All plans include 30-day money-back guarantee.
          </p>

          {/* Currency Toggle */}
          <div className="inline-flex items-center gap-1 p-1 rounded-xl bg-[var(--graphite-blue)]">
            <button
              onClick={() => setCurrency('usd')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                currency === 'usd'
                  ? 'bg-[var(--gold-accent)] text-[var(--void-black)]'
                  : 'text-[var(--cool-gray)] hover:text-[var(--soft-white)]'
              }`}
            >
              USD ($)
            </button>
            <button
              onClick={() => setCurrency('try')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                currency === 'try'
                  ? 'bg-[var(--gold-accent)] text-[var(--void-black)]'
                  : 'text-[var(--cool-gray)] hover:text-[var(--soft-white)]'
              }`}
            >
              TRY ({'\u20BA'})
            </button>
          </div>
        </div>

        {/* Legal Disclaimer - Required for paid services */}
        <div className="mb-6 max-w-4xl mx-auto">
          <div className="bg-amber-900/20 border border-amber-700/40 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-amber-300/70 leading-relaxed">
                <strong>Önemli Uyarı:</strong> Bu hizmetler yatırım danışmanlığı içermez.
                Tüm paketler yalnızca piyasa verisi ve analiz araçları sunar.
                SPK düzenlemeleri kapsamında yatırım tavsiyesi verilmemektedir.
              </p>
            </div>
          </div>
        </div>

        <div className="pricing-cards grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 max-w-7xl mx-auto">
          {/* Free Tier */}
          <div className="pricing-card glass-card p-6">
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-[var(--soft-white)] mb-1">Free</h3>
              <p className="text-sm text-[var(--cool-gray)]">Get started with gold</p>
            </div>
            <div className="mb-6">
              <span className="text-4xl font-bold text-[var(--soft-white)]">{currency === 'usd' ? '$0' : '\u20BA0'}</span>
              <span className="text-[var(--cool-gray)] ml-1">/month</span>
            </div>
            <a
              href="/app"
              onClick={() => trackPricingClick('free')}
              className="block w-full text-center py-3 rounded-xl font-semibold bg-[var(--graphite-blue)] text-[var(--soft-white)] hover:bg-[var(--deep-slate)] transition-colors mb-6"
            >
              Get Started
            </a>
            <div className="space-y-2.5">
              {features.map((f) => (
                <div key={f.name} className="flex items-center justify-between py-1.5 text-xs">
                  <span className="text-[var(--cool-gray)]">{f.name}</span>
                  <div className="flex items-center">{renderValue(f.free)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Starter Tier */}
          <div className="pricing-card glass-card p-6 relative border border-[var(--gold-accent)]/20">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[var(--gold-accent)]/20 text-[var(--gold-accent)] text-xs font-bold">
                <Zap size={12} />
                Best Value
              </span>
            </div>
            <div className="mb-6 mt-2">
              <h3 className="text-xl font-semibold text-[var(--soft-white)] mb-1">Starter</h3>
              <p className="text-sm text-[var(--cool-gray)]">Gold + Crypto</p>
            </div>
            <div className="mb-6">
              <span className="text-4xl font-bold text-[var(--soft-white)]">{p.starter}</span>
              <span className="text-[var(--cool-gray)] ml-1">/month</span>
              <div className="text-xs text-[var(--cool-gray)] mt-1">or {p.starterYear}/year (save {p.saveSt})</div>
            </div>
            <a
              href="/app"
              onClick={() => trackPricingClick('starter')}
              className="block w-full text-center py-3 rounded-xl font-semibold bg-gradient-to-r from-[var(--gold-accent)]/80 to-[var(--amber-pulse)]/80 text-[var(--void-black)] hover:opacity-90 transition-opacity mb-6"
            >
              Start Free Trial
            </a>
            <div className="space-y-2.5">
              {features.map((f) => (
                <div key={f.name} className="flex items-center justify-between py-1.5 text-xs">
                  <span className="text-[var(--cool-gray)]">{f.name}</span>
                  <div className="flex items-center">{renderValue(f.starter)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Pro Tier */}
          <div className="pricing-card glass-card p-6 relative border-2 border-[var(--gold-accent)]/40 shadow-lg shadow-[var(--gold-accent)]/20">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-gradient-to-r from-[var(--gold-accent)] to-[var(--amber-pulse)] text-[var(--void-black)] text-xs font-bold">
                <Sparkles size={12} />
                Most Popular
              </span>
            </div>
            <div className="mb-6 mt-2">
              <h3 className="text-xl font-semibold text-[var(--gold-accent)] mb-1">Pro</h3>
              <p className="text-sm text-[var(--cool-gray)]">All markets</p>
            </div>
            <div className="mb-6">
              <span className="text-4xl font-bold text-[var(--soft-white)]">{p.pro}</span>
              <span className="text-[var(--cool-gray)] ml-1">/month</span>
              <div className="text-xs text-[var(--cool-gray)] mt-1">or {p.proYear}/year (save {p.savePro})</div>
            </div>
            <a
              href="/app"
              onClick={() => trackPricingClick('pro')}
              className="block w-full text-center py-3 rounded-xl font-semibold bg-gradient-to-r from-[var(--gold-accent)] to-[var(--amber-pulse)] text-[var(--void-black)] hover:opacity-90 transition-opacity mb-6 shadow-lg"
            >
              Start Free Trial
            </a>
            <div className="space-y-2.5">
              {features.map((f) => (
                <div key={f.name} className="flex items-center justify-between py-1.5 text-xs">
                  <span className="text-[var(--cool-gray)]">{f.name}</span>
                  <div className="flex items-center">{renderValue(f.pro)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Pro Plus Tier */}
          <div className="pricing-card glass-card p-6 relative border border-[var(--gold-accent)]/20">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[var(--gold-accent)]/10 text-[var(--gold-accent)] text-xs font-bold">
                <Rocket size={12} />
                Full Access
              </span>
            </div>
            <div className="mb-6 mt-2">
              <h3 className="text-xl font-semibold text-[var(--soft-white)] mb-1">Pro Plus</h3>
              <p className="text-sm text-[var(--cool-gray)]">Power traders</p>
            </div>
            <div className="mb-6">
              <span className="text-4xl font-bold text-[var(--soft-white)]">{p.proPlus}</span>
              <span className="text-[var(--cool-gray)] ml-1">/month</span>
              <div className="text-xs text-[var(--cool-gray)] mt-1">or {p.proPlusYear}/year (save {p.saveProPlus})</div>
            </div>
            <a
              href="/app"
              onClick={() => trackPricingClick('pro_plus')}
              className="block w-full text-center py-3 rounded-xl font-semibold border-2 border-[var(--gold-accent)]/40 text-[var(--gold-accent)] hover:bg-[var(--gold-accent)]/10 transition-colors mb-6"
            >
              Start Free Trial
            </a>
            <div className="space-y-2.5">
              {features.map((f) => (
                <div key={f.name} className="flex items-center justify-between py-1.5 text-xs">
                  <span className="text-[var(--cool-gray)]">{f.name}</span>
                  <div className="flex items-center">{renderValue(f.proPlus)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Enterprise CTA */}
        <div className="mt-10 text-center">
          <div className="inline-flex items-center gap-3 px-8 py-4 rounded-2xl glass-card border border-[var(--gold-accent)]/20">
            <Crown size={24} className="text-[var(--gold-accent)]" />
            <div className="text-left">
              <p className="text-sm font-semibold text-[var(--soft-white)]">Enterprise</p>
              <p className="text-xs text-[var(--cool-gray)]">Custom API limits, white-label, SLA, dedicated support</p>
            </div>
            <a
              href="mailto:enterprise@sentilyze.com"
              onClick={() => trackPricingClick('enterprise')}
              className="ml-4 px-5 py-2 rounded-xl text-sm font-semibold border border-[var(--gold-accent)]/40 text-[var(--gold-accent)] hover:bg-[var(--gold-accent)]/10 transition-colors"
            >
              Contact Sales
            </a>
          </div>
        </div>

        {/* Trust badges */}
        <div className="mt-12 text-center">
          <div className="flex flex-wrap justify-center items-center gap-6 text-sm text-[var(--cool-gray)]">
            <div className="flex items-center gap-2">
              <Check size={16} className="text-[var(--lag-green)]" />
              <span>30-day money-back guarantee</span>
            </div>
            <div className="flex items-center gap-2">
              <Check size={16} className="text-[var(--lag-green)]" />
              <span>Cancel anytime</span>
            </div>
            <div className="flex items-center gap-2">
              <Check size={16} className="text-[var(--lag-green)]" />
              <span>No credit card required for free tier</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Pricing;

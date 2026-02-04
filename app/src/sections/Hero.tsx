import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ArrowRight, TrendingUp, ChevronDown, Sparkles } from 'lucide-react';

const Hero = () => {
  const heroRef = useRef<HTMLDivElement>(null);
  const headlineRef = useRef<HTMLHeadingElement>(null);

  // GSAP entrance animations
  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: 'expo.out' } });

      tl.fromTo(
        '.hero-headline-line',
        { y: 100, opacity: 0, rotateX: -30 },
        { y: 0, opacity: 1, rotateX: 0, duration: 0.8, stagger: 0.15 },
        0.4
      );

      tl.fromTo(
        '.hero-subheadline',
        { y: 30, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.6 },
        0.9
      );

      tl.fromTo(
        '.hero-cta-primary',
        { scale: 0.8, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.5, ease: 'back.out(1.7)' },
        1.1
      );

      tl.fromTo(
        '.hero-cta-secondary',
        { x: -20, opacity: 0 },
        { x: 0, opacity: 1, duration: 0.5 },
        1.2
      );

      tl.fromTo(
        '.hero-trust-badge',
        { scale: 0.9, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.4 },
        1.3
      );
    }, heroRef);

    return () => ctx.revert();
  }, []);

  return (
    <section
      ref={heroRef}
      className="relative min-h-screen flex flex-col overflow-hidden bg-[var(--bg-primary)]"
    >
      {/* Video Background */}
      <div className="absolute inset-0 z-0">
        <video
          autoPlay
          loop
          muted
          playsInline
          className="w-full h-full object-cover opacity-80"
        >
          <source src="/aurora-background.mp4" type="video/mp4" />
        </video>
        {/* Dark Overlay with Aurora accent - Reduced for brighter video */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#0A0E13]/60 via-[#0A0E13]/50 to-[#0A0E13]/70" />
        {/* Aurora glow effect */}
        <div className="absolute inset-0 bg-gradient-radial from-[var(--aurora-primary)]/5 via-transparent to-transparent" />
      </div>

      {/* Floating particles effect */}
      <div className="absolute inset-0 z-[1] opacity-30">
        <div className="absolute top-1/4 left-1/4 w-2 h-2 bg-[var(--aurora-primary)] rounded-full animate-pulse" />
        <div className="absolute top-1/3 right-1/3 w-1 h-1 bg-[var(--aurora-cyan)] rounded-full animate-pulse delay-100" />
        <div className="absolute bottom-1/3 left-1/3 w-1.5 h-1.5 bg-[var(--aurora-green)] rounded-full animate-pulse delay-200" />
      </div>

      {/* Main Hero Content */}
      <div className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="max-w-5xl mx-auto text-center relative">
          {/* Premium Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[var(--gold-light)] border border-[var(--gold-primary)]/30 mb-6 backdrop-blur-sm">
            <Sparkles className="w-4 h-4 text-[var(--gold-primary)]" />
            <span className="text-sm font-semibold text-[var(--gold-primary)]">
              AI-Powered Market Intelligence
            </span>
          </div>

          {/* Headline */}
          <h1
            ref={headlineRef}
            className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-6"
            style={{ perspective: '1000px' }}
          >
            <span className="hero-headline-line block text-[var(--text-primary)] drop-shadow-2xl">
              Read Market
            </span>
            <span className="hero-headline-line block bg-gradient-to-r from-[var(--aurora-cyan)] via-[var(--aurora-primary)] to-[var(--aurora-purple)] bg-clip-text text-transparent mt-2 drop-shadow-2xl animate-gradient">
              Sentiment with AI
            </span>
          </h1>

          {/* Subheadline */}
          <p className="hero-subheadline text-lg sm:text-xl text-[var(--text-secondary)] max-w-2xl mx-auto mb-10 leading-relaxed">
            Real-time sentiment analysis and price predictions for cryptocurrency and gold markets.
            Powered by Google Cloud&apos;s Vertex AI.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
            <a
              href="/app"
              className="hero-cta-primary group flex items-center gap-2 px-8 py-4 rounded-xl font-semibold bg-gradient-to-r from-[var(--gold-primary)] to-[var(--gold-soft)] hover:from-[var(--gold-hover)] hover:to-[var(--gold-primary)] transition-all duration-300 shadow-lg hover:shadow-2xl hover:shadow-[var(--gold-primary)]/50 hover:scale-105 text-[var(--bg-primary)]"
            >
              <TrendingUp size={20} />
              <span>Start Analysis</span>
              <ArrowRight size={18} className="ml-1 group-hover:translate-x-1 transition-transform" />
            </a>
            <a
              href="#gold-analysis"
              className="hero-cta-secondary flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-[var(--text-primary)] border border-[var(--border-color)] bg-[var(--bg-secondary)]/50 backdrop-blur-md hover:bg-[var(--bg-secondary)] hover:border-[var(--gold-primary)]/50 transition-all duration-300"
            >
              <span>Explore Features</span>
            </a>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-3 gap-4 sm:gap-8 max-w-3xl mx-auto mb-10">
            <div className="hero-trust-badge bg-[var(--bg-secondary)]/50 backdrop-blur-md border border-[var(--border-color)] rounded-xl p-4">
              <div className="text-2xl sm:text-3xl font-bold text-[var(--gold-primary)] mb-1">
                99.2%
              </div>
              <div className="text-xs sm:text-sm text-[var(--text-muted)]">
                API Uptime
              </div>
            </div>
            <div className="hero-trust-badge bg-[var(--bg-secondary)]/50 backdrop-blur-md border border-[var(--border-color)] rounded-xl p-4">
              <div className="text-2xl sm:text-3xl font-bold text-[var(--gold-primary)] mb-1">
                24/7
              </div>
              <div className="text-xs sm:text-sm text-[var(--text-muted)]">
                Live Analysis
              </div>
            </div>
            <div className="hero-trust-badge bg-[var(--bg-secondary)]/50 backdrop-blur-md border border-[var(--border-color)] rounded-xl p-4">
              <div className="text-2xl sm:text-3xl font-bold text-[var(--gold-primary)] mb-1">
                AI
              </div>
              <div className="text-xs sm:text-sm text-[var(--text-muted)]">
                Powered
              </div>
            </div>
          </div>

          {/* Google Cloud Startup Program Badge */}
          <div className="hero-trust-badge inline-flex items-center gap-3 px-5 py-3 rounded-xl bg-[var(--bg-secondary)]/50 border border-[var(--border-color)] backdrop-blur-md hover:bg-[var(--bg-secondary)] hover:border-[var(--gold-primary)]/30 transition-all duration-300">
            <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none">
                <path
                  d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"
                  fill="#4285F4"
                />
              </svg>
            </div>
            <div className="text-left">
              <p className="text-xs text-[var(--text-muted)]">Member of</p>
              <p className="text-sm font-semibold text-[var(--text-primary)]">
                Google Cloud Startup Program
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Scroll Indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-[var(--text-muted)] z-10">
        <span className="text-xs uppercase tracking-wider">Scroll to explore</span>
        <ChevronDown size={20} className="animate-bounce text-[var(--gold-primary)]" />
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[var(--bg-primary)] to-transparent z-[2]" />
    </section>
  );
};

export default Hero;

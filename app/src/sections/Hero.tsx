import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ArrowRight, TrendingUp, ChevronDown } from 'lucide-react';

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
      className="relative min-h-screen flex flex-col overflow-hidden"
    >
      {/* Video Background */}
      <div className="absolute inset-0 z-0">
        <video
          autoPlay
          loop
          muted
          playsInline
          className="w-full h-full object-cover"
        >
          <source src="/background.mp4" type="video/mp4" />
        </video>
        {/* Dark Overlay for better text readability */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/40 to-black/70" />
        {/* Additional gradient for depth */}
        <div className="absolute inset-0 bg-gradient-to-r from-black/30 via-transparent to-black/30" />
      </div>

      {/* Main Hero Content */}
      <div className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="max-w-5xl mx-auto text-center relative">
          {/* Headline */}
          <h1
            ref={headlineRef}
            className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-6"
            style={{ perspective: '1000px' }}
          >
            <span className="hero-headline-line block text-white drop-shadow-lg">
              Read Market
            </span>
            <span className="hero-headline-line block bg-gradient-to-r from-blue-400 via-purple-400 to-blue-400 bg-clip-text text-transparent mt-2 drop-shadow-lg">
              Sentiment with AI
            </span>
          </h1>

          {/* Subheadline */}
          <p className="hero-subheadline text-lg sm:text-xl text-gray-200 max-w-2xl mx-auto mb-10 leading-relaxed drop-shadow-md">
            Real-time sentiment analysis and price predictions for cryptocurrency and gold markets. 
            Powered by Google Cloud&apos;s Vertex AI.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
            <a
              href="#gold-analysis"
              className="hero-cta-primary flex items-center gap-2 px-8 py-4 rounded-xl text-white font-semibold bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-400 hover:to-purple-500 transition-all duration-300 shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 hover:scale-105"
            >
              <TrendingUp size={20} />
              <span>Explore Analysis</span>
              <ArrowRight size={18} className="ml-1" />
            </a>
            <a
              href="#how-it-works"
              className="hero-cta-secondary flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-white border border-white/30 bg-white/10 backdrop-blur-md hover:bg-white/20 hover:border-white/50 transition-all duration-300"
            >
              <span>View Architecture</span>
            </a>
          </div>

          {/* Google Cloud Startup Program Badge */}
          <div className="hero-trust-badge inline-flex items-center gap-3 px-5 py-3 rounded-xl bg-black/40 border border-white/20 backdrop-blur-md">
            <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none">
                <path
                  d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"
                  fill="#4285F4"
                />
              </svg>
            </div>
            <div className="text-left">
              <p className="text-xs text-gray-300">Member of</p>
              <p className="text-sm font-semibold text-white">
                Google Cloud Startup Program
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Scroll Indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-white/70 z-10">
        <span className="text-xs uppercase tracking-wider drop-shadow-md">Scroll to explore</span>
        <ChevronDown size={20} className="animate-bounce" />
      </div>
    </section>
  );
};

export default Hero;

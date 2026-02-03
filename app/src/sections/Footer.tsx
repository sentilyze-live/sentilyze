import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Twitter, Github, Linkedin, MessageCircle, AlertTriangle } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const Footer = () => {
  const footerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      // Top border animation
      gsap.fromTo(
        '.footer-border',
        { width: '0%' },
        {
          width: '100%',
          duration: 0.8,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: footerRef.current,
            start: 'top 90%',
          },
        }
      );

      // Content fade in
      gsap.fromTo(
        '.footer-content',
        { y: 30, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.6,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: footerRef.current,
            start: 'top 85%',
          },
        }
      );

      // Social icons
      gsap.fromTo(
        '.social-icon',
        { scale: 0, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 0.4,
          stagger: 0.08,
          ease: 'back.out(1.7)',
          scrollTrigger: {
            trigger: footerRef.current,
            start: 'top 80%',
          },
        }
      );
    }, footerRef);

    return () => ctx.revert();
  }, []);

  const socialLinks = [
    { icon: Twitter, href: '#', label: 'Twitter' },
    { icon: Github, href: '#', label: 'GitHub' },
    { icon: Linkedin, href: '#', label: 'LinkedIn' },
    { icon: MessageCircle, href: '#', label: 'Discord' },
  ];

  const footerLinks = [
    { label: 'Gizlilik Politikası', href: '#' },
    { label: 'Kullanım Şartları', href: '#' },
    { label: 'Risk Bildirimi', href: '#' },
    { label: 'İletişim', href: '#' },
  ];

  return (
    <footer
      ref={footerRef}
      className="relative py-16 overflow-hidden"
    >
      {/* Animated top border */}
      <div className="footer-border absolute top-0 left-1/2 -translate-x-1/2 h-px bg-gradient-to-r from-transparent via-[var(--signal-cyan)] to-transparent" />

      {/* Legal Disclaimer Banner */}
      <div className="section-container max-w-7xl mx-auto mb-8">
        <div className="bg-gradient-to-r from-amber-900/30 to-red-900/30 border border-amber-700/50 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-amber-400 font-semibold text-sm mb-1">YASAL UYARI VE RİSK BİLDİRİMİ</h3>
              <p className="text-xs text-amber-200/80 leading-relaxed">
                Sentilyze bir yatırım danışmanlığı platformu <strong>değildir</strong>. Sunulan tüm veriler, 
                yapay zeka modelleri tarafından üretilen <strong>bilgilendirme amaçlı senaryo analizleridir</strong> 
                ve kesinlik taşımaz. Bu platform, kullanıcılara yatırım tavsiyesi vermemektedir. 
                Herhangi bir finansal karar vermeden önce lisanslı bir yatırım danışmanına başvurmanız şiddetle önerilir. 
                Kripto para birimleri, altın ve diğer emtia piyasaları yüksek volatilite ve sermaye kaybı riski içerir. 
                Geçmiş performans gelecek performansın garantisi değildir. Tüm yatırım kararlarının sorumluluğu 
                tamamen kullanıcıya aittir.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="section-container max-w-7xl mx-auto">
        <div className="footer-content text-center">
          {/* Logo */}
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--signal-cyan)] to-[var(--lag-green)] flex items-center justify-center">
              <span className="text-[var(--void-black)] font-bold text-lg">S</span>
            </div>
            <span className="text-xl font-semibold text-[var(--soft-white)]">
              Sentilyze
            </span>
          </div>

          {/* Tagline */}
          <p className="text-[var(--cool-gray)] mb-2">
            AI Destekli Pazar Duygu Analizi Platformu
          </p>
          <p className="text-xs text-[var(--disabled-gray)] mb-8">
            Yatırım Danışmanlığı Değildir - Bilgilendirme Amaçlıdır
          </p>

          {/* Social Links */}
          <div className="flex items-center justify-center gap-4 mb-8">
            {socialLinks.map((social) => (
              <a
                key={social.label}
                href={social.href}
                className="social-icon w-10 h-10 rounded-lg bg-[var(--graphite-blue)] flex items-center justify-center text-[var(--cool-gray)] hover:text-[var(--signal-cyan)] hover:bg-[var(--deep-slate)] transition-all hover:-translate-y-1"
                aria-label={social.label}
              >
                <social.icon size={18} />
              </a>
            ))}
          </div>

          {/* Links */}
          <div className="flex items-center justify-center gap-6 mb-8 flex-wrap">
            {footerLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-sm text-[var(--cool-gray)] hover:text-[var(--soft-white)] transition-colors relative group"
              >
                {link.label}
                <span className="absolute -bottom-1 left-0 w-0 h-px bg-[var(--signal-cyan)] transition-all duration-300 group-hover:w-full" />
              </a>
            ))}
          </div>

          {/* Copyright */}
          <p className="text-xs text-[var(--disabled-gray)]">
            &copy; {new Date().getFullYear()} Sentilyze. Tüm hakları saklıdır.
          </p>
          <p className="text-xs text-[var(--disabled-gray)] mt-1">
            Bu platform 6362 sayılı SPK Kanunu kapsamında yatırım danışmanlığı faaliyeti yürütmemektedir.
          </p>

          {/* Google Cloud Badge */}
          <div className="mt-8 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--graphite-blue)]/50 border border-[var(--border)]">
            <div className="w-5 h-5 rounded bg-white flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-3 h-3" fill="none">
                <path
                  d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"
                  fill="#4285F4"
                />
              </svg>
            </div>
            <span className="text-xs text-[var(--cool-gray)]">
              Google Cloud Startup Program Member
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;

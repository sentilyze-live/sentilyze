import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Menu, X, LayoutDashboard, Sun, Moon } from 'lucide-react';

interface NavigationProps {
  isLightMode: boolean;
  onThemeToggle: () => void;
}

const Navigation = ({ isLightMode, onThemeToggle }: NavigationProps) => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Infrastructure', href: '#infrastructure' },
    { label: 'Gold Analysis', href: '#gold-analysis' },
    { label: 'Technology', href: '#technology' },
  ];

  const scrollToSection = (href: string) => {
    const element = document.querySelector(href);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
    setIsMobileMenuOpen(false);
  };

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? 'bg-[var(--bg-primary)]/80 backdrop-blur-xl border-b border-[var(--border-color)] py-3'
          : 'bg-transparent py-5'
      }`}
    >
      <div className="section-container max-w-7xl mx-auto">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <a
            href="#"
            className="flex items-center gap-2 group"
            onClick={(e) => {
              e.preventDefault();
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--gold-primary)] to-[var(--gold-soft)] flex items-center justify-center transition-transform duration-300 group-hover:scale-110 shadow-lg shadow-[var(--gold-primary)]/20">
              <span className="text-[var(--bg-primary)] font-bold text-sm">S</span>
            </div>
            <span className="text-lg font-semibold text-[var(--text-primary)] group-hover:text-[var(--gold-primary)] transition-colors drop-shadow-md">
              Sentilyze
            </span>
          </a>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <button
                key={link.href}
                onClick={() => scrollToSection(link.href)}
                className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors relative group drop-shadow-md"
              >
                {link.label}
                <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-[var(--gold-primary)] transition-all duration-300 group-hover:w-full" />
              </button>
            ))}
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-3">
            {/* Theme Toggle */}
            <button
              onClick={onThemeToggle}
              className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-all"
              aria-label="Toggle theme"
            >
              {isLightMode ? <Moon size={18} /> : <Sun size={18} />}
            </button>

            {/* Dashboard Button - Redirects to /app */}
            <button
              onClick={() => navigate('/app')}
              className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--gold-primary)]/50 text-[var(--gold-primary)] hover:bg-[var(--gold-light)] hover:border-[var(--gold-primary)] transition-all font-medium"
            >
              <LayoutDashboard size={16} />
              <span className="text-sm">Dashboard</span>
            </button>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-all"
              aria-label="Toggle menu"
            >
              {isMobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden mt-4 py-4 border-t border-[var(--border-color)] bg-[var(--bg-secondary)]/90 backdrop-blur-xl rounded-lg">
            <div className="flex flex-col gap-4 px-4">
              {navLinks.map((link) => (
                <button
                  key={link.href}
                  onClick={() => scrollToSection(link.href)}
                  className="text-left text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors py-2"
                >
                  {link.label}
                </button>
              ))}
              <button
                onClick={() => {
                  navigate('/app');
                  setIsMobileMenuOpen(false);
                }}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--gold-primary)]/50 text-[var(--gold-primary)] hover:bg-[var(--gold-light)] transition-all mt-2 font-medium"
              >
                <LayoutDashboard size={16} />
                <span className="text-sm">Dashboard</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navigation;

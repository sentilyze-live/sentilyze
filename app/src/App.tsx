import { useEffect, useState, useRef } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Toaster } from 'sonner';
import Navigation from './sections/Navigation';
import Hero from './sections/Hero';
import HowItWorks from './sections/HowItWorks';
import GoogleCloud from './sections/GoogleCloud';
import GoldAnalysis from './sections/GoldAnalysis';
import SocialProof from './sections/SocialProof';
import Pricing from './sections/Pricing';
import BlogPreview from './sections/BlogPreview';
import FAQ from './sections/FAQ';
import NewsletterCTA from './sections/NewsletterCTA';
import Footer from './sections/Footer';
import DashboardPage from './pages/DashboardPage';
import LegalPage from './pages/LegalPage';
import Blog from './sections/Blog';
import BlogPost from './sections/BlogPost';
import DashboardLayout from './components/DashboardLayout';
import CookieConsent from './components/legal/CookieConsent';
import CookieSettings from './components/legal/CookieSettings';
import './App.css';

gsap.registerPlugin(ScrollTrigger);

// Skip to content link for accessibility
const SkipToContent: React.FC = () => {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-blue-500 focus:text-white focus:rounded-lg"
    >
      Ana içeriğe atla
    </a>
  );
};



const LandingPage: React.FC = () => {
  const [isLightMode, setIsLightMode] = useState(false);
  const mainRef = useRef<HTMLDivElement>(null);

  // Apply aurora theme for landing page
  useEffect(() => {
    document.documentElement.setAttribute('data-landing-theme', 'aurora');

    return () => {
      document.documentElement.removeAttribute('data-landing-theme');
    };
  }, []);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.utils.toArray<HTMLElement>('.reveal-section').forEach((section) => {
        gsap.fromTo(
          section,
          { opacity: 0.9, y: 30 },
          {
            opacity: 1,
            y: 0,
            duration: 0.6,
            ease: 'power2.out',
            scrollTrigger: {
              trigger: section,
              start: 'top 85%',
              toggleActions: 'play none none none',
            },
          }
        );
      });
    }, mainRef);

    return () => ctx.revert();
  }, []);

  const toggleTheme = () => {
    setIsLightMode(!isLightMode);
    document.documentElement.classList.toggle('light');
  };

  return (
    <div ref={mainRef} className="min-h-screen bg-[var(--void-black)]">
      <SkipToContent />
      <Navigation 
        isLightMode={isLightMode}
        onThemeToggle={toggleTheme}
      />
      
      <main id="main-content">
        <Hero />
        <HowItWorks />
        <GoldAnalysis />
        <SocialProof />
        <Pricing />
        <GoogleCloud />
        <BlogPreview />
        <FAQ />
        <NewsletterCTA />
      </main>

      <Footer />
    </div>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--bg-card)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
          },
        }}
      />
      <CookieConsent />
      <CookieSettings />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/app" element={<DashboardLayout><DashboardPage /></DashboardLayout>} />
        <Route path="/blog" element={<Blog />} />
        <Route path="/blog/:slug" element={<BlogPost />} />
        <Route path="/legal/:type" element={<LegalPage />} />
        <Route path="/admin/*" element={<Navigate to="/admin/login" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
